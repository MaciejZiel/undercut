"""Session replay data (FR-701): one compact, pre-aggregated, cacheable timeline of a race.

The frontend plays a race back with a timeline at up to 60x, so the payload is a fixed-step
sampling (default 5 s) of the whole session, never raw rows.

Time base: t = 0 is the start of lap 1 (earliest lap 1 `date_start` of all drivers); `t` values
are seconds from that moment. Frame i has t = i * step.

Carry-forward: every frame value is the last known sample at or before t (position, gap,
interval, lap start). Before a driver's first sample the value is null (lap: the first lap).
Samples earlier than t = 0 (the pre-race grid, up to one hour) take part in carry-forward.

Encoding (column arrays, aligned to `frames.t`):
- dense, one value per frame: `pos`, `gap` (leader gap), `int` (interval to the car ahead).
  Gap and interval are integer milliseconds, or text such as "+1 LAP", or null.
- run encoded, because they change rarely: `lap`, `tyre`, `age`, `pit`. Each is
  {"at": [frame index, ...], "v": [value, ...]}; the value holds from that frame index until
  the next entry (the first entry is always at frame 0).
`frames.drivers[k]` belongs to `drivers[k]`.

Cost: 6 queries here plus the 2 of the caller (header, drivers), independent of the data size.
Per driver every stream is merged against the frame grid with one forward pointer, so the work
is O(samples + frames).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from django.db.models import Q

from apps.catalog.lookups import SessionHeader, session_drivers

from . import selectors
from .models import IntervalSample, PitStop, PositionSample, RaceControlMessage, Stint

DEFAULT_STEP = 5
MIN_STEP = 1
MAX_STEP = 30
PRE_RACE_WINDOW_S = 3600  # samples this long before the start still feed carry-forward
DEFAULT_LANE_MS = 22_000  # pit lane window when the lane duration is unknown


def _carry(times: list[float], values: list[Any], grid: list[float], default: Any = None) -> list:
    """Last value with time <= grid point, for every grid point. Both inputs sorted."""
    out = []
    j = 0
    n = len(times)
    current = default
    for g in grid:
        while j < n and times[j] <= g:
            current = values[j]
            j += 1
        out.append(current)
    return out


def _runs(values: list[Any]) -> dict[str, list]:
    at: list[int] = []
    v: list[Any] = []
    for index, value in enumerate(values):
        if index == 0 or value != v[-1]:
            at.append(index)
            v.append(value)
    return {"at": at, "v": v}


def _round(value: float) -> float:
    return round(value, 3)


class _Timeline:
    """Lap data of the session: time base, per driver lap windows and the lap clock."""

    def __init__(self, header: SessionHeader):
        self.laps_by_driver = selectors._load_laps(header.session_id)
        self.windows = {d: selectors._lap_windows(laps) for d, laps in self.laps_by_driver.items()}
        starts_lap1 = [
            start
            for ws in self.windows.values()
            for number, start, _ in ws
            if number == 1 and start
        ]
        all_starts = [s for ws in self.windows.values() for _, s, _ in ws if s]
        if not all_starts:
            raise selectors._no_data(header)
        self.start = min(starts_lap1 or all_starts).timestamp()
        ends = [e for ws in self.windows.values() for _, _, e in ws if e]
        self.end = max(ends + all_starts).timestamp()
        self.total_laps = max(n for ws in self.windows.values() for n, _, _ in ws)
        self.earliest: dict[int, float] = {}
        for ws in self.windows.values():
            for number, start, _ in ws:
                if start is not None:
                    value = start.timestamp()
                    if number not in self.earliest or value < self.earliest[number]:
                        self.earliest[number] = value
        self.lap_for = selectors._lap_resolver(self.laps_by_driver)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def offset(self, ts) -> float:
        return _round(max(0.0, ts.timestamp() - self.start))

    def leader_finish(self) -> float | None:
        """End of the final lap of the first driver that completed every lap."""
        finishes = [
            ws[-1][2].timestamp()
            for ws in self.windows.values()
            if ws and ws[-1][0] == self.total_laps and ws[-1][2] is not None
        ]
        return min(finishes) if finishes else None


def lap_offsets(header: SessionHeader) -> dict[str, Any]:
    """Jump-to-lap helpers: lap number -> t offset of the leader's lap start (3 queries total)."""
    line = _Timeline(header)
    numbers = sorted(line.earliest)
    return {
        "session": _session_block(header),
        "total_laps": line.total_laps,
        "duration_s": _round(line.duration),
        "laps": [{"lap": n, "t": _round(max(0.0, line.earliest[n] - line.start))} for n in numbers],
    }


def _session_block(header: SessionHeader) -> dict[str, Any]:
    return {
        "year": header.year,
        "round": header.round,
        "round_name": header.round_name,
        "type": header.type,
        "status": header.status,
    }


def replay(header: SessionHeader, step: int = DEFAULT_STEP) -> dict[str, Any]:
    """The whole replay document (8 queries including the header)."""
    drivers = session_drivers(header.session_id, header.type)
    if not drivers:
        raise selectors._no_data(header)
    line = _Timeline(header)
    count = int(line.duration // step) + 1
    grid_t = [i * step for i in range(count)]
    grid = [line.start + t for t in grid_t]

    lower = line.start - PRE_RACE_WINDOW_S
    sid = header.session_id
    positions = _group(
        PositionSample.objects.filter(session_id=sid, ts__gte=_dt(lower), ts__lte=_dt(grid[-1]))
        .order_by("driver_id", "ts")
        .values_list("driver_id", "ts", "position")
    )
    intervals = _group(
        IntervalSample.objects.filter(session_id=sid, ts__gte=_dt(lower), ts__lte=_dt(grid[-1]))
        .order_by("driver_id", "ts")
        .values_list(
            "driver_id",
            "ts",
            "gap_to_leader_ms",
            "gap_to_leader_text",
            "interval_ms",
            "interval_text",
        )
    )
    stints: dict[int, list[tuple]] = {}
    for driver_id, lap_start, compound, age in (
        Stint.objects.filter(session_id=sid)
        .order_by("driver_id", "stint_number")
        .values_list("driver_id", "lap_start", "compound", "tyre_age_at_start")
    ):
        stints.setdefault(driver_id, []).append((lap_start or 1, compound, age or 0))
    pit_rows = list(
        PitStop.objects.filter(session_id=sid)
        .order_by("driver_id", "date")
        .values_list("driver_id", "date", "lap_number", "lane_ms")
    )
    messages = list(
        RaceControlMessage.objects.filter(session_id=sid)
        .filter(Q(category__iexact="SafetyCar") | Q(flag__in=["RED", "CHEQUERED"]))
        .order_by("ts", "id")
        .values_list("ts", "lap_number", "category", "flag", "scope", "message")
    )

    pit_windows: dict[int, list[tuple[float, float]]] = {}
    for driver_id, date, _lap, lane_ms in pit_rows:
        begin = date.timestamp()
        pit_windows.setdefault(driver_id, []).append(
            (begin, begin + (lane_ms if lane_ms else DEFAULT_LANE_MS) / 1000)
        )

    driver_blocks = []
    frame_blocks = []
    retired_after = {}
    for d in drivers:
        did = d.driver_id
        laps = line.windows.get(did, [])
        retired_t = None
        if laps and laps[-1][2] is None and laps[-1][0] < line.total_laps and laps[-1][1]:
            retired_t = _round(max(0.0, laps[-1][1].timestamp() - line.start))
        retired_after[did] = retired_t
        driver_blocks.append(
            {
                "driver_id": did,
                "code": d.code,
                "full_name": d.full_name,
                "constructor_name": d.constructor_name,
                "color_hex": d.color_hex,
                "retired_t": retired_t,
            }
        )
        frame_blocks.append(
            _driver_frames(
                grid,
                laps,
                stints.get(did, []),
                positions.get(did, ([], [])),
                intervals.get(did, ([], [])),
                pit_windows.get(did, []),
            )
        )

    return {
        "session": {
            **_session_block(header),
            "start": _dt(line.start).isoformat(),
            "end": _dt(line.end).isoformat(),
            "laps": line.total_laps,
            "duration_s": _round(line.duration),
        },
        "drivers": driver_blocks,
        "frames": {
            "step_s": step,
            "count": count,
            "t": grid_t,
            "drivers": frame_blocks,
        },
        "events": _events(line, messages, pit_rows, drivers),
    }


def _dt(epoch: float):
    return datetime.fromtimestamp(epoch, tz=UTC)


def _group(rows) -> dict[int, tuple[list[float], list]]:
    """driver id -> (sorted epoch times, values) from rows (driver_id, ts, *values)."""
    out: dict[int, tuple[list[float], list]] = {}
    for driver_id, ts, *rest in rows:
        times, values = out.setdefault(driver_id, ([], []))
        times.append(ts.timestamp())
        values.append(rest[0] if len(rest) == 1 else tuple(rest))
    return out


def _gap(ms, text):
    if ms is not None:
        return ms
    return text or None


def _driver_frames(grid, laps, stints, positions, intervals, pits) -> dict[str, Any]:
    pos = _carry(positions[0], positions[1], grid)

    gap_times = intervals[0]
    gaps = _carry(gap_times, [_gap(v[0], v[1]) for v in intervals[1]], grid)
    ints = _carry(gap_times, [_gap(v[2], v[3]) for v in intervals[1]], grid)

    starts = [(s.timestamp(), n) for n, s, _ in laps if s is not None]
    lap_series = (
        _carry([s for s, _ in starts], [n for _, n in starts], grid, default=starts[0][1])
        if starts
        else [None] * len(grid)
    )

    tyre: list[Any] = [None] * len(grid)
    age: list[Any] = [None] * len(grid)
    if stints:
        k = 0
        for i, lap in enumerate(lap_series):
            if lap is None:
                continue
            while k + 1 < len(stints) and stints[k + 1][0] <= lap:
                k += 1
            first_lap, compound, base_age = stints[k]
            tyre[i] = compound
            age[i] = base_age + max(0, lap - first_lap)

    pit = []
    p = 0
    for g in grid:
        while p < len(pits) and pits[p][1] <= g:
            p += 1
        pit.append(1 if p < len(pits) and pits[p][0] <= g else 0)

    return {
        "pos": pos,
        "gap": gaps,
        "int": ints,
        "lap": _runs(lap_series),
        "tyre": _runs(tyre),
        "age": _runs(age),
        "pit": _runs(pit),
    }


def _events(line: _Timeline, messages, pit_rows, drivers) -> list[dict[str, Any]]:
    """Markers sorted by time: start, pit, safety_car / vsc (with an end), red_flag, chequered."""
    code = {d.driver_id: d.code for d in drivers}

    def lap_at(ts) -> int:
        return line.lap_for(ts)

    def event(kind, t, lap, label, driver=None, end_t=None, end_lap=None):
        return {
            "kind": kind,
            "t": t,
            "lap": lap,
            "label": label,
            "driver": driver,
            "end_t": end_t,
            "end_lap": end_lap,
        }

    events = [event("start", 0.0, 1, "Race start")]
    for driver_id, date, lap_number, _lane in pit_rows:
        if driver_id in code:
            lap = lap_number or lap_at(date)
            events.append(
                event("pit", line.offset(date), lap, f"{code[driver_id]} pit stop", code[driver_id])
            )

    opened: dict[str, tuple] = {}
    chequered = None
    for ts, lap_number, category, flag, scope, message in messages:
        lap = lap_number or lap_at(ts)
        text = message.upper()
        if category.lower() == "safetycar":
            kind = "vsc" if ("VIRTUAL" in text or "VSC" in text) else "safety_car"
            if "DEPLOYED" in text:
                opened.setdefault(kind, (ts, lap))
            elif "IN THIS LAP" in text or "ENDING" in text:
                begun = opened.pop(kind, None)
                if begun is not None:
                    events.append(_neutral(line, event, kind, begun, (ts, max(lap, begun[1]))))
        elif flag == "RED" and scope in ("", "Track"):
            events.append(event("red_flag", line.offset(ts), lap, "Red flag"))
        elif flag == "CHEQUERED" and chequered is None and ts.timestamp() >= line.start:
            chequered = (line.offset(ts), lap)
    for kind, begun in opened.items():
        events.append(_neutral(line, event, kind, begun, None))

    if chequered is None:
        finish = line.leader_finish()
        chequered = (_round((finish if finish else line.end) - line.start), line.total_laps)
    events.append(event("chequered", chequered[0], chequered[1], "Chequered flag"))

    order = {"start": 0, "chequered": 9}
    events.sort(key=lambda e: (e["t"], order.get(e["kind"], 5)))
    return events


def _neutral(line, event, kind, begun, ended):
    label = "Virtual safety car" if kind == "vsc" else "Safety car"
    end_t = line.offset(ended[0]) if ended else _round(line.duration)
    end_lap = ended[1] if ended else line.total_laps
    return event(kind, line.offset(begun[0]), begun[1], label, None, end_t, end_lap)


__all__ = ["DEFAULT_STEP", "MAX_STEP", "MIN_STEP", "lap_offsets", "replay"]

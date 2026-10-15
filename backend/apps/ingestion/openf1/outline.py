"""Track outlines from OpenF1 car positions (FR-205).

For every circuit raced since 2023 one clean lap of the race winner is requested (laps, then the
car's x/y samples for exactly that lap), simplified to a short closed polyline and stored on the
circuit. The track length is measured on the raw samples; it is an estimate (the racing line is a
little shorter than the centre line), and the API says so.

OpenF1 x/y are in decimetres. Three small requests per circuit, nothing is imported twice: a
circuit that has an outline is skipped unless `force` is set.
"""

from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import dataclass, field

from django.db import transaction

from apps.catalog import scheduling
from apps.catalog import services as catalog

from . import matching
from . import schemas as s
from .client import OpenF1Client, OpenF1Error
from .mapper import parse_ts

log = logging.getLogger(__name__)

FIRST_YEAR = 2023  # OpenF1 starts in 2023
VIEWBOX = 1000  # the longer side of the outline is scaled to this many units
SIMPLIFY_TOLERANCE = 1.5  # in viewBox units (0.15 % of the long side)
MIN_SAMPLES = 100  # a lap has about 370 at 3.7 Hz; fewer means missing data
MIN_CLOSURE = 0.08  # first and last sample must be within this share of the long side
DECIMETRES = 10


def _perpendicular(point, start, end) -> float:
    (px, py), (sx, sy), (ex, ey) = point, start, end
    dx, dy = ex - sx, ey - sy
    if dx == 0 and dy == 0:
        return math.dist(point, start)
    return abs(dy * px - dx * py + ex * sy - ey * sx) / math.hypot(dx, dy)


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker without recursion (laps have hundreds of points, not millions)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst, index = 0.0, None
        for i in range(first + 1, last):
            distance = _perpendicular(points[i], points[first], points[last])
            if distance > worst:
                worst, index = distance, i
        if index is not None and worst > tolerance:
            keep[index] = True
            stack.extend([(first, index), (index, last)])
    return [p for p, k in zip(points, keep, strict=True) if k]


def path_length(points: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:], strict=False))


def build_outline(
    samples: list[tuple[float, float]], *, min_samples: int = MIN_SAMPLES
) -> dict | None:
    """Closed, simplified, normalised outline from raw x/y samples of one lap; None if unusable."""
    if len(samples) < min_samples:
        return None
    xs, ys = [p[0] for p in samples], [p[1] for p in samples]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    longest = max(width, height)
    if longest <= 0:
        return None
    # A lap starts and ends on the line, so the ends must be close; otherwise the window was wrong.
    if math.dist(samples[0], samples[-1]) > MIN_CLOSURE * longest:
        return None
    length_m = path_length([*samples, samples[0]]) / DECIMETRES
    scale = VIEWBOX / longest
    # y is flipped: map coordinates grow upwards, SVG grows downwards.
    scaled = [((x - min(xs)) * scale, (max(ys) - y) * scale) for x, y in samples]
    points = simplify([*scaled, scaled[0]], SIMPLIFY_TOLERANCE)
    return {
        "width": round(width * scale),
        "height": round(height * scale),
        "points": [[round(x), round(y)] for x, y in points],
        "length_m": round(length_m),
    }


def pick_lap(laps: list[dict]) -> dict | None:
    """A representative racing lap: not an out lap, closest to the median duration."""
    usable = [
        lap
        for lap in laps
        if lap.get("date_start")
        and lap.get("lap_duration")
        and not lap.get("is_pit_out_lap")
        and (lap.get("lap_number") or 0) >= 2
    ]
    if not usable:
        return None
    durations = sorted(lap["lap_duration"] for lap in usable)
    median = durations[len(durations) // 2]
    return min(usable, key=lambda lap: abs(lap["lap_duration"] - median))


def _fmt(moment: dt.datetime) -> str:
    return moment.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")


def fetch_outline(client: OpenF1Client, session_key: int) -> dict | None:
    """Outline from the winner's median lap of one race session, or None when data is missing."""
    winner = client.get("session_result", {"session_key": session_key, "position": 1})
    number = winner[0].get("driver_number") if winner else None
    if number is None:
        return None
    lap = pick_lap(client.get("laps", {"session_key": session_key, "driver_number": number}))
    start = parse_ts(lap["date_start"]) if lap else None
    if lap is None or start is None:
        return None
    stop = start + dt.timedelta(seconds=float(lap["lap_duration"]))
    rows = client.get(
        "location",
        {
            "session_key": session_key,
            "driver_number": number,
            "date>=": _fmt(start),
            "date<=": _fmt(stop),
        },
    )
    samples = [
        (float(r["x"]), float(r["y"]))
        for r in sorted(rows, key=lambda r: r.get("date", ""))
        if r.get("x") is not None and r.get("y") is not None
    ]
    return build_outline(samples)


@dataclass
class OutlineSummary:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def import_outlines(
    client: OpenF1Client,
    *,
    years: list[int] | None = None,
    round_number: int | None = None,
    force: bool = False,
    now: dt.datetime | None = None,
) -> OutlineSummary:
    """Write outlines for circuits that have none, newest layout first (newest year wins)."""
    now = now or dt.datetime.now(dt.UTC)
    summary = OutlineSummary()
    handled: set[int] = set()
    for year in sorted(years or range(FIRST_YEAR, now.year + 1), reverse=True):
        meetings = s.Meeting.parse_all(client.get("meetings", {"year": year}))
        sessions = s.Session.parse_all(client.get("sessions", {"year": year}))
        if not meetings or not sessions:
            continue
        with transaction.atomic():
            match = matching.match_year(year, meetings, sessions)
        races = [
            m
            for m in match.sessions
            if m.type == "RACE" and (round_number is None or m.round_number == round_number)
        ]
        for ms in sorted(races, key=lambda m: m.round_number or 0, reverse=True):
            if ms.end_utc is None or ms.end_utc > now:
                continue
            target = scheduling.outline_target(ms.session_id)
            label = f"{year} {ms.round_name}"
            if target is None or target.circuit_id in handled:
                continue
            if target.has_outline and not force:
                handled.add(target.circuit_id)
                summary.skipped.append(label)
                continue
            try:
                outline = fetch_outline(client, ms.session_key)
            except OpenF1Error as exc:
                log.warning("Outline request failed for %s: %s", label, exc)
                summary.failed.append(f"{label}: {exc}")
                continue
            if outline is None:
                summary.failed.append(f"{label}: no usable lap")
                continue
            catalog.set_circuit_outline(
                target.circuit_id, {**outline, "source": {"year": year, "round": ms.round_number}}
            )
            handled.add(target.circuit_id)
            summary.written.append(label)
    return summary

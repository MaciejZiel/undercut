"""Maps OpenF1 identifiers onto the catalog.

- meeting -> Round: same year, race date within +-3 days of the meeting end, same country
  (or, when country names differ in spelling, a matching location or circuit name);
- session -> catalog Session: by type within the matched round;
- driver_number -> Driver, per season: name_acronym == Driver.code, then normalised surname.

Nothing is guessed. Anything ambiguous or unmatched becomes an error dict that the importer
writes to SyncRun.errors; an admin can fix drivers in DriverNumberMap, which always wins.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field

from apps.catalog import services as catalog
from apps.ingestion.models import DriverNumberMap

from . import schemas as s
from .mapper import parse_ts

DATE_TOLERANCE_DAYS = 3

SESSION_TYPES = {
    "practice 1": "FP1",
    "practice 2": "FP2",
    "practice 3": "FP3",
    "sprint qualifying": "SQ",
    "sprint shootout": "SQ",  # the 2023 name
    "sprint": "SPRINT",
    "qualifying": "Q",
    "race": "RACE",
}
# Practice is optional data: a missing catalog session is noted, not reported as an error.
OPTIONAL_TYPES = frozenset({"FP1", "FP2", "FP3"})

_COUNTRY_ALIASES = {
    "usa": "united states",
    "united states of america": "united states",
    "uae": "united arab emirates",
    "uk": "united kingdom",
    "great britain": "united kingdom",
    "korea": "south korea",
    "republic of korea": "south korea",
    "holland": "netherlands",
}


def session_type_for(session_name: str | None) -> str | None:
    """OpenF1 session name to catalog Session.Type value (None for e.g. testing days)."""
    return SESSION_TYPES.get((session_name or "").strip().casefold())


def normalise(value: str | None) -> str:
    """Lowercase, no diacritics, letters and digits only ("Pérez" -> "perez")."""
    value = (value or "").translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O"}))
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", "", stripped.casefold())


def _country(value: str | None) -> str:
    key = " ".join((value or "").casefold().split())
    return normalise(_COUNTRY_ALIASES.get(key, key))


@dataclass(frozen=True)
class MatchedSession:
    session_id: int
    session_key: int
    type: str
    round_id: int
    year: int
    round_number: int | None
    round_name: str
    status: str
    start_utc: dt.datetime | None
    end_utc: dt.datetime | None
    meeting_key: int


@dataclass
class YearMatch:
    sessions: list[MatchedSession] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # benign skips (testing, missing FP, ...)
    keys_set: int = 0


def _meeting_date(meeting: s.Meeting) -> dt.date | None:
    end = parse_ts(meeting.date_end)
    if end:
        return end.date()
    start = parse_ts(meeting.date_start)
    return (start + dt.timedelta(days=2)).date() if start else None


def _hint_match(meeting: s.Meeting, rnd: catalog.RoundRef) -> bool:
    hints = {normalise(meeting.location), normalise(meeting.circuit_short_name)} - {""}
    targets = [normalise(rnd.locality), normalise(rnd.circuit_name), normalise(rnd.name)]
    return any(h in t or (t and t in h) for h in hints for t in targets if t)


def match_meeting(
    meeting: s.Meeting, rounds: list[catalog.RoundRef]
) -> tuple[catalog.RoundRef | None, str]:
    """Returns (round, "") or (None, reason)."""
    when = _meeting_date(meeting)
    if when is None:
        return None, "meeting has no usable date"
    near = [r for r in rounds if abs((r.date - when).days) <= DATE_TOLERANCE_DAYS]
    if not near:
        return None, f"no round within {DATE_TOLERANCE_DAYS} days of {when}"
    wanted = _country(meeting.country_name)
    same_country = [r for r in near if wanted and _country(r.country) == wanted]
    candidates = same_country or [r for r in near if _hint_match(meeting, r)]
    if not candidates:
        return None, f"date matches {[r.name for r in near]} but country/location differ"
    if len(candidates) > 1:
        best = min(abs((r.date - when).days) for r in candidates)
        candidates = [r for r in candidates if abs((r.date - when).days) == best]
    if len(candidates) > 1:
        return None, f"ambiguous: {[r.name for r in candidates]}"
    return candidates[0], ""


def match_year(
    year: int,
    meetings: list[s.Meeting],
    sessions: list[s.Session],
    *,
    meeting_keys: set[int] | None = None,
) -> YearMatch:
    """Match a year's OpenF1 meetings and sessions to the catalog and store the keys."""
    result = YearMatch()
    rounds = catalog.season_rounds(year)
    by_meeting: dict[int, list[s.Session]] = {}
    for sess in sessions:
        if sess.meeting_key is not None:
            by_meeting.setdefault(sess.meeting_key, []).append(sess)

    for meeting in meetings:
        key = meeting.meeting_key
        if key is None or (meeting_keys is not None and key not in meeting_keys):
            continue
        label = meeting.meeting_name or str(key)
        if meeting.is_cancelled:
            result.notes.append(f"{year} {label}: cancelled, skipped")
            continue
        if "testing" in (meeting.meeting_name or "").casefold():
            result.notes.append(f"{year} {label}: testing, skipped")
            continue
        rnd, reason = match_meeting(meeting, rounds)
        if rnd is None:
            result.errors.append(
                {
                    "type": "unmatched_meeting",
                    "year": year,
                    "meeting_key": key,
                    "meeting": label,
                    "error": reason,
                }
            )
            continue
        try:
            result.keys_set += catalog.set_openf1_meeting_key(rnd.id, key)
        except ValueError as exc:
            result.errors.append(
                {
                    "type": "meeting_key_conflict",
                    "year": year,
                    "meeting_key": key,
                    "round_id": rnd.id,
                    "error": str(exc),
                }
            )
            continue
        _match_sessions(year, meeting, rnd, by_meeting.get(key, []), result)
    return result


def _match_sessions(
    year: int,
    meeting: s.Meeting,
    rnd: catalog.RoundRef,
    of1_sessions: list[s.Session],
    result: YearMatch,
) -> None:
    ours = {ref.type: ref for ref in catalog.round_sessions(rnd.id)}
    seen: dict[str, s.Session] = {}
    for sess in of1_sessions:
        if sess.session_key is None or sess.is_cancelled:
            continue
        kind = session_type_for(sess.session_name)
        where = f"{year} {meeting.meeting_name} / {sess.session_name}"
        if kind is None:
            result.notes.append(f"{where}: unknown session name, skipped")
            continue
        if kind in seen:
            result.errors.append(
                {
                    "type": "ambiguous_session",
                    "year": year,
                    "session_key": sess.session_key,
                    "error": f"{where}: second OpenF1 session of type {kind}",
                }
            )
            continue
        seen[kind] = sess
        ref = ours.get(kind)
        if ref is None:
            if kind in OPTIONAL_TYPES:
                result.notes.append(f"{where}: no catalog session, skipped")
            else:
                result.errors.append(
                    {
                        "type": "unmatched_session",
                        "year": year,
                        "session_key": sess.session_key,
                        "error": f"{where}: round {rnd.id} has no {kind} session",
                    }
                )
            continue
        try:
            result.keys_set += catalog.set_openf1_session_key(ref.id, sess.session_key)
        except ValueError as exc:
            result.errors.append(
                {
                    "type": "session_key_conflict",
                    "year": year,
                    "session_key": sess.session_key,
                    "session_id": ref.id,
                    "error": str(exc),
                }
            )
            continue
        result.sessions.append(
            MatchedSession(
                session_id=ref.id,
                session_key=sess.session_key,
                type=kind,
                round_id=rnd.id,
                year=year,
                round_number=rnd.number,
                round_name=rnd.name,
                status=ref.status,
                start_utc=parse_ts(sess.date_start) or ref.start_utc,
                end_utc=parse_ts(sess.date_end) or ref.end_utc,
                meeting_key=meeting.meeting_key or 0,
            )
        )


# --------------------------------------------------------------------------- drivers


@dataclass
class DriverResolution:
    mapping: dict[int, int] = field(default_factory=dict)  # driver_number -> driver id
    unmatched: list[dict] = field(default_factory=list)
    created: int = 0


def _single(candidates: list[catalog.DriverRef]) -> int | None:
    ids = {c.id for c in candidates}
    return ids.pop() if len(ids) == 1 else None


def resolve_drivers(year: int, drivers: list[s.Driver]) -> DriverResolution:
    """Number -> driver id for one season. Existing DriverNumberMap rows win and are kept."""
    out = DriverResolution()
    existing = dict(
        DriverNumberMap.objects.filter(season_year=year).values_list("driver_number", "driver_id")
    )
    out.mapping.update(existing)
    pool = catalog.season_drivers(year)

    for drv in drivers:
        number = drv.driver_number
        if number is None or number in out.mapping:
            continue
        driver_id = None
        code = (drv.name_acronym or "").strip().upper()
        if code:
            driver_id = _single([d for d in pool if d.code.upper() == code])
            if driver_id is None and not any(d.code.upper() == code for d in pool):
                driver_id = _single(catalog.drivers_by_code(code))
        if driver_id is None:
            tail = (drv.full_name or "").split()[-1:]
            surname = normalise(drv.last_name) or normalise(tail[0] if tail else "")
            if surname:
                driver_id = _single([d for d in pool if normalise(d.family_name) == surname])
        if driver_id is None:
            out.unmatched.append(
                {
                    "type": "unmatched_driver",
                    "year": year,
                    "driver_number": number,
                    "name_acronym": drv.name_acronym,
                    "full_name": drv.full_name,
                    "error": "no catalog driver matches; add it to DriverNumberMap",
                }
            )
            continue
        _, created = DriverNumberMap.objects.get_or_create(
            season_year=year, driver_number=number, defaults={"driver_id": driver_id}
        )
        out.created += created
        out.mapping[number] = driver_id
    return out

"""Public write interface of the catalog module.

Other modules (ingestion, ...) never import `apps.catalog.models`; they hand plain dataclasses to
the functions here and get ids and counters back. Everything is an idempotent upsert on a natural
key: running the same input twice creates nothing and reports every row as unchanged.

Results flagged `manual_override` are never touched; they are counted in `skipped_manual` when the
incoming data would have changed them.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils.text import slugify

from . import models as m

# --------------------------------------------------------------------------- inputs


@dataclass(frozen=True)
class SeasonData:
    year: int
    name: str = ""


@dataclass(frozen=True)
class CircuitData:
    jolpica_id: str
    name: str
    slug: str = ""
    locality: str = ""
    country: str = ""
    lat: Decimal | None = None
    lng: Decimal | None = None
    timezone: str = ""


@dataclass(frozen=True)
class DriverData:
    jolpica_id: str
    given_name: str
    family_name: str
    slug: str = ""
    code: str = ""
    permanent_number: int | None = None
    dob: dt.date | None = None
    nationality: str = ""


@dataclass(frozen=True)
class ConstructorData:
    jolpica_id: str
    name: str
    slug: str = ""
    nationality: str = ""


@dataclass(frozen=True)
class ConstructorSeasonData:
    constructor_jolpica_id: str
    year: int
    display_name: str = ""
    color_hex: str | None = None


@dataclass(frozen=True)
class RoundData:
    year: int
    round: int | None
    name: str
    circuit_jolpica_id: str
    date: dt.date
    scheduled_laps: int | None = None
    is_cancelled: bool = False


@dataclass(frozen=True)
class SessionData:
    type: str  # a `Session.Type` value
    start_utc: dt.datetime | None = None
    # None = leave an existing session's status alone (a new one starts as "scheduled").
    # The calendar sync uses it so it can never downgrade a session that already has results.
    status: str | None = "scheduled"
    end_utc: dt.datetime | None = None


@dataclass(frozen=True)
class ResultData:
    driver_jolpica_id: str
    constructor_jolpica_id: str
    position: int | None = None
    position_text: str = ""
    grid: int | None = None
    laps: int | None = None
    status: str = ""
    time_ms: int | None = None
    best_lap_ms: int | None = None
    points: Decimal = Decimal(0)
    fastest_lap_rank: int | None = None


@dataclass(frozen=True)
class QualifyingData:
    driver_jolpica_id: str
    constructor_jolpica_id: str
    position: int | None = None
    q1_ms: int | None = None
    q2_ms: int | None = None
    q3_ms: int | None = None


@dataclass(frozen=True)
class SessionBundle:
    session: SessionData
    results: Sequence[ResultData] = ()
    qualifying: Sequence[QualifyingData] = ()


@dataclass(frozen=True)
class RoundBundle:
    round: RoundData
    sessions: Sequence[SessionBundle] = ()


# --------------------------------------------------------------------------- outputs


@dataclass(frozen=True)
class Outcome:
    id: int
    created: bool
    updated: bool = False


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_manual: int = 0

    def add(self, other: Counts) -> None:
        self.created += other.created
        self.updated += other.updated
        self.unchanged += other.unchanged
        self.skipped_manual += other.skipped_manual

    def record(self, outcome: Outcome) -> None:
        if outcome.created:
            self.created += 1
        elif outcome.updated:
            self.updated += 1
        else:
            self.unchanged += 1


@dataclass
class RoundOutcome:
    round_id: int
    round: Outcome
    sessions: Counts = field(default_factory=Counts)
    results: Counts = field(default_factory=Counts)
    qualifying: Counts = field(default_factory=Counts)


class MissingReference(LookupError):
    """An input points at a driver, constructor, circuit or season that is not in the catalog."""


# --------------------------------------------------------------------------- helpers


def _sync(model, lookup: dict, values: dict, *, fill_blank_only: Iterable[str] = ()) -> Outcome:
    """get-or-create on `lookup`; save only when a value actually differs."""
    blank_only = set(fill_blank_only)
    obj = model.objects.filter(**lookup).first()
    if obj is None:
        plain = {k: v for k, v in lookup.items() if "__" not in k}  # drop e.g. round__isnull
        obj = model.objects.create(**plain, **values)
        return Outcome(obj.pk, created=True)
    dirty = []
    for name, value in values.items():
        current = getattr(obj, name)
        if name in blank_only and current not in (None, ""):
            continue
        if current != value:
            setattr(obj, name, value)
            dirty.append(name)
    if dirty:
        obj.save(update_fields=dirty)
    return Outcome(obj.pk, created=False, updated=bool(dirty))


def _slug(preferred: str, fallback: str) -> str:
    return slugify((preferred or fallback).replace("_", "-"))


def _ids(model, jolpica_ids: Iterable[str]) -> dict[str, int]:
    wanted = {i for i in jolpica_ids if i}
    found = dict(model.objects.filter(jolpica_id__in=wanted).values_list("jolpica_id", "pk"))
    missing = wanted - found.keys()
    if missing:
        raise MissingReference(f"{model.__name__} not in catalog: {sorted(missing)[:5]}")
    return found


# --------------------------------------------------------------------------- reference data


def upsert_season(data: SeasonData) -> Outcome:
    return _sync(m.Season, {"year": data.year}, {"name": data.name}, fill_blank_only=["name"])


def _create_with_slug(model, jolpica_id: str, slug: str, values: dict) -> Outcome:
    """Create-or-update where the slug is only chosen on create (it is part of public URLs)."""
    obj = model.objects.filter(jolpica_id=jolpica_id).first()
    if obj is not None:
        return _sync(model, {"jolpica_id": jolpica_id}, values)
    base = slug or slugify(jolpica_id)
    candidate, n = base, 1
    while model.objects.filter(slug=candidate).exists():
        n += 1
        candidate = f"{base}-{n}"
    obj = model.objects.create(jolpica_id=jolpica_id, slug=candidate, **values)
    return Outcome(obj.pk, created=True)


def upsert_circuit(data: CircuitData) -> Outcome:
    values = {
        "name": data.name,
        "locality": data.locality,
        "country": data.country,
        "lat": data.lat,
        "lng": data.lng,
    }
    if data.timezone:
        values["timezone"] = data.timezone
    return _create_with_slug(m.Circuit, data.jolpica_id, _slug(data.slug, data.jolpica_id), values)


def upsert_driver(data: DriverData) -> Outcome:
    values = {
        "given_name": data.given_name,
        "family_name": data.family_name,
        "code": data.code,
        "permanent_number": data.permanent_number,
        "dob": data.dob,
        "nationality": data.nationality,
    }
    return _create_with_slug(m.Driver, data.jolpica_id, _slug(data.slug, data.jolpica_id), values)


def upsert_constructor(data: ConstructorData) -> Outcome:
    values = {"name": data.name, "nationality": data.nationality}
    return _create_with_slug(
        m.Constructor, data.jolpica_id, _slug(data.slug, data.jolpica_id), values
    )


def upsert_constructor_season(data: ConstructorSeasonData) -> Outcome:
    """Display name and colour are editable by hand, so they are only filled while blank."""
    try:
        constructor_id = m.Constructor.objects.values_list("pk", flat=True).get(
            jolpica_id=data.constructor_jolpica_id
        )
        season_id = m.Season.objects.values_list("pk", flat=True).get(year=data.year)
    except (m.Constructor.DoesNotExist, m.Season.DoesNotExist) as exc:
        raise MissingReference(f"{data.constructor_jolpica_id} / {data.year}") from exc
    return _sync(
        m.ConstructorSeason,
        {"constructor_id": constructor_id, "season_id": season_id},
        {"display_name": data.display_name, "color_hex": data.color_hex},
        fill_blank_only=["display_name", "color_hex"],
    )


# --------------------------------------------------------------------------- calendar


def upsert_round(data: RoundData) -> Outcome:
    try:
        season_id = m.Season.objects.values_list("pk", flat=True).get(year=data.year)
    except m.Season.DoesNotExist as exc:
        raise MissingReference(f"Season {data.year}") from exc
    circuit_id = _ids(m.Circuit, [data.circuit_jolpica_id])[data.circuit_jolpica_id]
    values = {
        "name": data.name,
        "circuit_id": circuit_id,
        "scheduled_laps": data.scheduled_laps,
        "is_cancelled": data.is_cancelled,
    }
    if data.round is not None:
        return _sync(
            m.Round,
            {"season_id": season_id, "round": data.round},
            {**values, "date": data.date},
        )
    # A round without a number (a cancelled one) is identified by its date.
    return _sync(
        m.Round,
        {"season_id": season_id, "round__isnull": True, "date": data.date},
        values,
    )


def upsert_session(round_id: int, data: SessionData) -> Outcome:
    values: dict = {}
    if data.status is not None:
        values["status"] = data.status
    if data.start_utc is not None:  # never replace a known start time with "unknown"
        values["start_utc"] = data.start_utc
    if data.end_utc is not None:
        values["end_utc"] = data.end_utc
    return _sync(m.Session, {"round_id": round_id, "type": data.type}, values)


# --------------------------------------------------------------------------- results


_RESULT_FIELDS = (
    "constructor_id",
    "position",
    "position_text",
    "grid",
    "laps",
    "status",
    "time_ms",
    "best_lap_ms",
    "points",
    "fastest_lap_rank",
)


def _bulk_sync(
    model,
    session_id: int,
    wanted: dict[int, dict],
    fields: Sequence[str],
    *,
    honour_manual: bool,
) -> Counts:
    """Diff `wanted` (driver_id -> values) against the session's rows and write the difference."""
    counts = Counts()
    existing = {o.driver_id: o for o in model.objects.filter(session_id=session_id)}
    to_create, to_update = [], []
    taken_by_locked: set[int] = set()
    if honour_manual:
        taken_by_locked = {
            o.position for o in existing.values() if o.manual_override and o.position is not None
        }
    for driver_id, values in wanted.items():
        obj = existing.get(driver_id)
        if obj is None:
            if values.get("position") in taken_by_locked:
                values = {**values, "position": None}
            to_create.append(model(session_id=session_id, driver_id=driver_id, **values))
            continue
        changed = [f for f in fields if getattr(obj, f) != values[f]]
        if honour_manual and obj.manual_override:
            if changed:
                counts.skipped_manual += 1
            else:
                counts.unchanged += 1
            continue
        if not changed:
            counts.unchanged += 1
            continue
        if "position" in changed and values["position"] in taken_by_locked:
            values = {**values, "position": None}
        for f in changed:
            setattr(obj, f, values[f])
        to_update.append((obj, changed))
    if to_update:
        # Free unique slots first so reshuffled positions / fastest-lap flags cannot collide.
        release = [f for f in ("position", "fastest_lap_rank") if hasattr(model, f)]
        freed = []
        for obj, changed in to_update:
            hit = [f for f in release if f in changed]
            if hit:
                snapshot = {f: getattr(obj, f) for f in hit}
                for f in hit:
                    setattr(obj, f, None)
                freed.append((obj, hit, snapshot))
        if freed:
            model.objects.bulk_update([o for o, _, _ in freed], release)
            for obj, hit, snapshot in freed:
                for f in hit:
                    setattr(obj, f, snapshot[f])
        union = sorted({f for _, changed in to_update for f in changed})
        model.objects.bulk_update([o for o, _ in to_update], union)
        counts.updated += len(to_update)
    if to_create:
        model.objects.bulk_create(to_create)
        counts.created += len(to_create)
    return counts


def upsert_results(session_id: int, rows: Sequence[ResultData]) -> Counts:
    drivers = _ids(m.Driver, (r.driver_jolpica_id for r in rows))
    constructors = _ids(m.Constructor, (r.constructor_jolpica_id for r in rows))
    wanted = {
        drivers[r.driver_jolpica_id]: {
            "constructor_id": constructors[r.constructor_jolpica_id],
            "position": r.position,
            "position_text": r.position_text,
            "grid": r.grid,
            "laps": r.laps,
            "status": r.status,
            "time_ms": r.time_ms,
            "best_lap_ms": r.best_lap_ms,
            "points": r.points,
            "fastest_lap_rank": r.fastest_lap_rank,
        }
        for r in rows
    }
    return _bulk_sync(m.Result, session_id, wanted, _RESULT_FIELDS, honour_manual=True)


def upsert_qualifying(session_id: int, rows: Sequence[QualifyingData]) -> Counts:
    drivers = _ids(m.Driver, (r.driver_jolpica_id for r in rows))
    constructors = _ids(m.Constructor, (r.constructor_jolpica_id for r in rows))
    wanted = {
        drivers[r.driver_jolpica_id]: {
            "constructor_id": constructors[r.constructor_jolpica_id],
            "position": r.position,
            "q1_ms": r.q1_ms,
            "q2_ms": r.q2_ms,
            "q3_ms": r.q3_ms,
        }
        for r in rows
    }
    fields = ("constructor_id", "position", "q1_ms", "q2_ms", "q3_ms")
    return _bulk_sync(m.QualifyingResult, session_id, wanted, fields, honour_manual=False)


@transaction.atomic
def import_round(bundle: RoundBundle) -> RoundOutcome:
    """Upsert one round with its sessions and results: one round, one transaction."""
    round_outcome = upsert_round(bundle.round)
    outcome = RoundOutcome(round_id=round_outcome.id, round=round_outcome)
    for item in bundle.sessions:
        session = upsert_session(round_outcome.id, item.session)
        outcome.sessions.record(session)
        if item.results:
            outcome.results.add(upsert_results(session.id, item.results))
        if item.qualifying:
            outcome.qualifying.add(upsert_qualifying(session.id, item.qualifying))
    return outcome


# --------------------------------------------------------------------------- OpenF1 matching
# Read helpers and key setters for the OpenF1 importer. Plain dataclasses in, plain dataclasses
# out: the ingestion module never sees catalog models.


@dataclass(frozen=True)
class RoundRef:
    id: int
    year: int
    number: int | None
    name: str
    date: dt.date
    is_cancelled: bool
    circuit_name: str
    locality: str
    country: str
    openf1_meeting_key: int | None


@dataclass(frozen=True)
class SessionRef:
    id: int
    round_id: int
    type: str
    status: str
    start_utc: dt.datetime | None
    end_utc: dt.datetime | None
    openf1_session_key: int | None


@dataclass(frozen=True)
class DriverRef:
    id: int
    code: str
    given_name: str
    family_name: str


def season_rounds(year: int) -> list[RoundRef]:
    """All rounds of a season (cancelled ones included), ordered by date."""
    rows = m.Round.objects.filter(season__year=year).select_related("circuit").order_by("date")
    return [
        RoundRef(
            id=r.pk,
            year=year,
            number=r.round,
            name=r.name,
            date=r.date,
            is_cancelled=r.is_cancelled,
            circuit_name=r.circuit.name,
            locality=r.circuit.locality,
            country=r.circuit.country,
            openf1_meeting_key=r.openf1_meeting_key,
        )
        for r in rows
    ]


def round_sessions(round_id: int) -> list[SessionRef]:
    rows = m.Session.objects.filter(round_id=round_id).order_by("start_utc", "type")
    return [
        SessionRef(
            id=s.pk,
            round_id=round_id,
            type=s.type,
            status=s.status,
            start_utc=s.start_utc,
            end_utc=s.end_utc,
            openf1_session_key=s.openf1_session_key,
        )
        for s in rows
    ]


def set_openf1_meeting_key(round_id: int, meeting_key: int) -> bool:
    """Store the OpenF1 meeting key. Returns False when nothing changed.

    Raises ValueError when the key already belongs to another round or the round has a
    different key: the importer reports it instead of overwriting a possibly manual fix.
    """
    obj = m.Round.objects.get(pk=round_id)
    if obj.openf1_meeting_key == meeting_key:
        return False
    if obj.openf1_meeting_key is not None:
        raise ValueError(f"round {round_id} already has meeting key {obj.openf1_meeting_key}")
    if m.Round.objects.filter(openf1_meeting_key=meeting_key).exists():
        raise ValueError(f"meeting key {meeting_key} already belongs to another round")
    obj.openf1_meeting_key = meeting_key
    obj.save(update_fields=["openf1_meeting_key"])
    return True


def set_openf1_session_key(session_id: int, session_key: int) -> bool:
    """Same contract as `set_openf1_meeting_key`, for sessions."""
    obj = m.Session.objects.get(pk=session_id)
    if obj.openf1_session_key == session_key:
        return False
    if obj.openf1_session_key is not None:
        raise ValueError(f"session {session_id} already has session key {obj.openf1_session_key}")
    if m.Session.objects.filter(openf1_session_key=session_key).exists():
        raise ValueError(f"session key {session_key} already belongs to another session")
    obj.openf1_session_key = session_key
    obj.save(update_fields=["openf1_session_key"])
    return True


def _driver_refs(qs) -> list[DriverRef]:
    return [
        DriverRef(id=d.pk, code=d.code, given_name=d.given_name, family_name=d.family_name)
        for d in qs
    ]


def season_drivers(year: int) -> list[DriverRef]:
    """Drivers with a race or qualifying result in the season (the candidates for matching)."""
    ids = set(
        m.Result.objects.filter(session__round__season__year=year).values_list(
            "driver_id", flat=True
        )
    ) | set(
        m.QualifyingResult.objects.filter(session__round__season__year=year).values_list(
            "driver_id", flat=True
        )
    )
    return _driver_refs(m.Driver.objects.filter(pk__in=ids).order_by("pk"))


def drivers_by_code(code: str) -> list[DriverRef]:
    """Every driver with this three-letter code, any season (empty code matches nothing)."""
    if not code:
        return []
    return _driver_refs(m.Driver.objects.filter(code__iexact=code).order_by("pk"))

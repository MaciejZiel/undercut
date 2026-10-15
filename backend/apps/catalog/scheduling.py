"""Read helpers for scheduling and syncing: which sessions need results, round lookups."""

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Q

from . import models as m

SYNCED_TYPES = (m.Session.Type.RACE, m.Session.Type.SPRINT, m.Session.Type.Q)


@dataclass(frozen=True)
class SessionRef:
    id: int
    year: int
    round: int | None
    type: str
    status: str
    start_utc: dt.datetime | None
    end_utc: dt.datetime | None


def _ref(session: m.Session) -> SessionRef:
    return SessionRef(
        id=session.pk,
        year=session.round.season.year,
        round=session.round.round,
        type=session.type,
        status=session.status,
        start_utc=session.start_utc,
        end_utc=session.end_utc,
    )


def session_ref(session_id: int) -> SessionRef | None:
    session = m.Session.objects.select_related("round__season").filter(pk=session_id).first()
    return _ref(session) if session else None


def sessions_awaiting_results(
    now: dt.datetime, *, after: dt.timedelta, until: dt.timedelta
) -> list[SessionRef]:
    """Sessions that ended between `until` and `after` ago and are not final yet."""
    sessions = (
        m.Session.objects.select_related("round__season")
        .filter(
            type__in=SYNCED_TYPES,
            end_utc__lte=now - after,
            end_utc__gte=now - until,
            round__is_cancelled=False,
        )
        .exclude(status=m.Session.Status.RESULTS_FINAL)
    )
    return [_ref(s) for s in sessions]


def practice_awaiting_results(
    now: dt.datetime, *, after: dt.timedelta, until: dt.timedelta, since_year: int
) -> list[SessionRef]:
    """Practice sessions that ended between `until` and `after` ago and are not final yet."""
    sessions = (
        m.Session.objects.select_related("round__season")
        .filter(
            type__in=("FP1", "FP2", "FP3"),
            end_utc__lte=now - after,
            end_utc__gte=now - until,
            round__is_cancelled=False,
            round__season__year__gte=since_year,
        )
        .exclude(status=m.Session.Status.RESULTS_FINAL)
    )
    return [_ref(s) for s in sessions]


def set_session_status(session_id: int, status: str) -> bool:
    """Returns True when the status changed."""
    return bool(
        m.Session.objects.filter(pk=session_id).exclude(status=status).update(status=status)
    )


def current_season_year(today: dt.date) -> int | None:
    """The season being run: the latest one that has rounds starting on or before next month."""
    year = (
        m.Round.objects.filter(date__lte=today + dt.timedelta(days=45))
        .order_by("-season__year")
        .values_list("season__year", flat=True)
        .first()
    )
    return year


def latest_finished_round(now: dt.datetime, *, within: dt.timedelta) -> tuple[int, int] | None:
    """(year, round number) of the most recent round whose race ended within `within`."""
    session = (
        m.Session.objects.filter(
            type=m.Session.Type.RACE,
            end_utc__lte=now,
            end_utc__gte=now - within,
            round__round__isnull=False,
        )
        .select_related("round__season")
        .order_by("-end_utc")
        .first()
    )
    return (session.round.season.year, session.round.round) if session else None


def round_sessions(year: int, number: int) -> list[SessionRef]:
    sessions = m.Session.objects.select_related("round__season").filter(
        round__season__year=year, round__round=number
    )
    return [_ref(s) for s in sessions]


def mark_missing_rounds_cancelled(year: int, present_rounds: set[int]) -> list[int]:
    """Rounds we hold that the source no longer lists are cancelled, never deleted."""
    stale = list(
        m.Round.objects.filter(season__year=year, is_cancelled=False, round__isnull=False)
        .exclude(round__in=present_rounds)
        .values_list("round", flat=True)
    )
    if stale:
        m.Round.objects.filter(season__year=year, round__in=stale).update(is_cancelled=True)
    return stale


def podium_counts(season_id: int, upto_round: int) -> tuple[dict[str, int], dict[str, int]]:
    """Classified top-3 race finishes up to a round, per driver and per constructor (per car)."""
    podium = Q(position__lte=3) & Q(position_text__regex=r"^\d+$")
    base = m.Result.objects.filter(
        session__type=m.Session.Type.RACE,
        session__round__season_id=season_id,
        session__round__round__lte=upto_round,
    ).filter(podium)
    drivers = dict(
        base.values("driver__jolpica_id")
        .annotate(n=Count("id"))
        .values_list("driver__jolpica_id", "n")
    )
    teams = dict(
        base.values("constructor__jolpica_id")
        .annotate(n=Count("id"))
        .values_list("constructor__jolpica_id", "n")
    )
    return drivers, teams


def qualifying_started(now: dt.datetime, *, within: dt.timedelta) -> list[tuple[int, dt.datetime]]:
    """(round id, start) of qualifying sessions that started within the last `within`."""
    sessions = m.Session.objects.filter(
        type=m.Session.Type.Q,
        start_utc__lte=now,
        start_utc__gte=now - within,
        round__is_cancelled=False,
    ).values_list("round_id", "start_utc")
    return list(sessions)


def sessions_ended_between(
    now: dt.datetime, *, after: dt.timedelta, until: dt.timedelta, types: Sequence[str]
) -> list[SessionRef]:
    """Sessions of the given types that ended between `until` and `after` ago."""
    sessions = m.Session.objects.select_related("round__season").filter(
        type__in=types,
        end_utc__lte=now - after,
        end_utc__gte=now - until,
        round__is_cancelled=False,
        round__round__isnull=False,
    )
    return [_ref(s) for s in sessions]


@dataclass(frozen=True)
class OutlineTarget:
    circuit_id: int
    slug: str
    has_outline: bool


def outline_target(session_id: int) -> OutlineTarget | None:
    """The circuit of a session and whether it already has a track outline."""
    session = m.Session.objects.filter(pk=session_id).select_related("round__circuit").first()
    if session is None:
        return None
    circuit = session.round.circuit
    return OutlineTarget(circuit.id, circuit.slug, bool(circuit.outline))


def has_results(session_id: int) -> bool:
    """Whether the session has race-style or qualifying rows."""
    return (
        m.Result.objects.filter(session_id=session_id).exists()
        or m.QualifyingResult.objects.filter(session_id=session_id).exists()
    )

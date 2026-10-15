"""Small public read functions of the catalog for other modules (no model imports needed).

Other modules call these instead of importing catalog models. Everything returns plain frozen
dataclasses, and every function costs a fixed number of queries.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import F, OuterRef, Subquery

from .models import ConstructorSeason, QualifyingResult, Result, Session


@dataclass(frozen=True)
class SessionHeader:
    """A session with the round it belongs to."""

    session_id: int
    year: int
    round: int
    round_name: str
    type: str
    status: str

    @property
    def is_final(self) -> bool:
        return self.status in (Session.Status.FINISHED, Session.Status.RESULTS_FINAL)


@dataclass(frozen=True)
class SessionDriver:
    """A driver in a session with the constructor on that day and its season colour."""

    driver_id: int
    code: str
    full_name: str
    constructor_id: int
    constructor_name: str
    color_hex: str | None  # None means "neutral colour"
    position: int | None  # final classification, None when unclassified


def get_session_header(year: int, round_number: int, session_type: str) -> SessionHeader | None:
    """The session of a round (1 query), or None when the round or the session is missing."""
    row = (
        Session.objects.filter(
            round__season__year=year, round__round=round_number, type=session_type
        )
        .values("id", "round__season__year", "round__round", "round__name", "type", "status")
        .first()
    )
    if row is None:
        return None
    return SessionHeader(
        session_id=row["id"],
        year=row["round__season__year"],
        round=row["round__round"],
        round_name=row["round__name"],
        type=row["type"],
        status=row["status"],
    )


def session_drivers(session_id: int, session_type: str) -> list[SessionDriver]:
    """Drivers of a session in final order (unclassified last), 1 query (2 when falling back).

    Reads Result rows (QualifyingResult for a qualifying session) and falls back to the other
    table when the first is empty.
    """
    sources = [QualifyingResult, Result]
    if session_type != Session.Type.Q:
        sources.reverse()
    for model in sources:
        rows = _driver_rows(model, session_id)
        if rows:
            return rows
    return []


def _driver_rows(model: type[Result] | type[QualifyingResult], session_id: int):
    colour = ConstructorSeason.objects.filter(
        constructor=OuterRef("constructor_id"), season=OuterRef("session__round__season_id")
    ).values("color_hex")[:1]
    rows = (
        model.objects.filter(session_id=session_id)
        .annotate(color=Subquery(colour))
        .order_by(F("position").asc(nulls_last=True), "driver_id")
        .values_list(
            "driver_id",
            "driver__code",
            "driver__given_name",
            "driver__family_name",
            "constructor_id",
            "constructor__name",
            "color",
            "position",
        )
    )
    return [
        SessionDriver(
            driver_id=driver_id,
            code=code or family[:3].upper(),
            full_name=f"{given} {family}".strip(),
            constructor_id=constructor_id,
            constructor_name=constructor_name,
            color_hex=color or None,
            position=position,
        )
        for (
            driver_id,
            code,
            given,
            family,
            constructor_id,
            constructor_name,
            color,
            position,
        ) in rows
    ]

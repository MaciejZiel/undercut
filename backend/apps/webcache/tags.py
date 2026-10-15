"""Cache tags of the frontend (see frontend/src/lib/api/queries.ts) for each kind of change.

Round pages carry `season:<year>` and `round:<year>-<n>`, season pages `seasons` and
`season:<year>`, detail pages also carry their list tag (`drivers`, `constructors`, ...), so
purging a list tag refreshes every page of that kind.
"""

from __future__ import annotations

from apps.catalog import references, scheduling


def season(year: int) -> str:
    return f"season:{year}"


def round_(year: int, number: int) -> str:
    return f"round:{year}-{number}"


def for_session(session_id: int, *, results_changed: bool) -> set[str]:
    ref = scheduling.session_ref(session_id)
    if ref is None:
        return set()
    tags = {season(ref.year)}
    if ref.round is not None:
        tags.add(round_(ref.year, ref.round))
    if results_changed:
        # Results move driver and team statistics, circuit winners and season calendars.
        tags |= {"drivers", "constructors", "circuits", "seasons"}
    return tags


def for_standings(year: int) -> set[str]:
    # Titles shown on driver and constructor pages come from the standings.
    return {"standings", season(year), "seasons", "drivers", "constructors"}


def for_history_import(from_year: int | None, to_year: int | None) -> set[str]:
    years = [
        y
        for y in references.season_ids_by_year()
        if (from_year is None or y >= from_year) and (to_year is None or y <= to_year)
    ]
    base = {"drivers", "constructors", "circuits", "seasons", "standings", "search"}
    return base | {season(y) for y in years}

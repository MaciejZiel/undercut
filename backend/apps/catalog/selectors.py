"""Read queries of the catalog module.

Everything the public read API needs lives here so views stay thin. Missing data is returned as
None (never as zero); counts are real counts of stored rows.

Conventions:
- "starts", "wins", "podiums" and "fastest laps" are counted over RACE sessions only.
- "points" add RACE and SPRINT sessions.
- Pole positions come from grid == 1 on race sessions before POLE_QUALIFYING_FROM_YEAR and from
  qualifying position 1 afterwards.
- Titles are not derivable from this module (they need the standings module): always None.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import (
    Count,
    Exists,
    F,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
)
from django.utils import timezone

from .models import (
    Circuit,
    Constructor,
    ConstructorSeason,
    Driver,
    QualifyingResult,
    Result,
    Round,
    Season,
    Session,
)
from .text import make_search_name

POLE_QUALIFYING_FROM_YEAR = 1994
SEARCH_MIN_LENGTH = 2
SEARCH_GROUP_LIMIT = 5
LAST_RESULTS_LIMIT = 10

RACE = Session.Type.RACE
SPRINT = Session.Type.SPRINT
QUALIFYING = Session.Type.Q

DRIVER_ORDERINGS = {
    "family_name": ("family_name", "given_name"),
    "wins": ("wins", "family_name"),
    "starts": ("starts", "family_name"),
    # Titles need the standings module; until then this falls back to the name order.
    "titles": ("family_name", "given_name"),
}
CONSTRUCTOR_ORDERINGS = {
    "name": ("name",),
    "wins": ("wins", "name"),
    "starts": ("starts", "name"),
}
CIRCUIT_ORDERINGS = {
    "name": ("name",),
    "country": ("country", "name"),
    "gp_count": ("gp_count", "name"),
    "last_gp_date": ("last_gp_date", "name"),
}


def _number(value: Decimal | int | float | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _ordered(queryset: QuerySet, orderings: dict, key: str) -> QuerySet:
    """Apply a validated ordering key such as "-wins" (descending when prefixed with "-")."""
    descending = key.startswith("-")
    fields = orderings[key.lstrip("-")]
    if descending:
        fields = tuple(f"-{name}" for name in fields)
    return queryset.order_by(*fields, "pk")


def team_ref(slug, name, color) -> dict | None:
    if slug is None:
        return None
    return {"slug": slug, "name": name, "color": color}


def season_colors(year: int) -> dict[int, str | None]:
    """Constructor id -> team colour for one season (missing entries mean a neutral colour)."""
    return dict(
        ConstructorSeason.objects.filter(season__year=year).values_list(
            "constructor_id", "color_hex"
        )
    )


def color_map(years, constructor_ids) -> dict[tuple[int, int], str | None]:
    """(season year, constructor id) -> team colour, in one query."""
    return {
        (year, constructor_id): color
        for year, constructor_id, color in ConstructorSeason.objects.filter(
            season__year__in=list(years), constructor_id__in=list(constructor_ids)
        ).values_list("season__year", "constructor_id", "color_hex")
    }


def latest_result_year() -> int | None:
    return Result.objects.aggregate(year=Max("session__round__season__year"))["year"]


# --- Drivers ---------------------------------------------------------------------------------


def driver_list(
    *,
    season: int | None = None,
    nationality: str | None = None,
    constructor: str | None = None,
    active: bool | None = None,
    q: str | None = None,
    ordering: str = "family_name",
) -> QuerySet:
    race = Q(results__session__type=RACE)
    last_race = Result.objects.filter(driver=OuterRef("pk"), session__type=RACE).order_by(
        "-session__round__date", "-session_id"
    )
    queryset = Driver.objects.annotate(
        starts=Count("results", filter=race),
        wins=Count("results", filter=race & Q(results__position=1)),
        last_constructor_id=Subquery(last_race.values("constructor_id")[:1]),
        last_constructor_slug=Subquery(last_race.values("constructor__slug")[:1]),
        last_constructor_name=Subquery(last_race.values("constructor__name")[:1]),
        last_season_year=Subquery(last_race.values("session__round__season__year")[:1]),
    ).annotate(
        last_constructor_color=Subquery(
            ConstructorSeason.objects.filter(
                constructor_id=OuterRef("last_constructor_id"),
                season__year=OuterRef("last_season_year"),
            ).values("color_hex")[:1]
        )
    )
    # Filters use EXISTS so they never multiply the joined rows used by the counters above.
    if season is not None:
        queryset = queryset.filter(
            Exists(
                Result.objects.filter(driver=OuterRef("pk"), session__round__season__year=season)
            )
        )
    if constructor:
        queryset = queryset.filter(
            Exists(Result.objects.filter(driver=OuterRef("pk"), constructor__slug=constructor))
        )
    if nationality:
        queryset = queryset.filter(nationality__iexact=nationality)
    if q:
        queryset = queryset.filter(search_name__contains=make_search_name(q))
    if active is not None:
        year = latest_result_year()
        in_latest = Exists(
            Result.objects.filter(driver=OuterRef("pk"), session__round__season__year=year)
        )
        queryset = queryset.filter(in_latest if active else ~in_latest)
    return _ordered(queryset, DRIVER_ORDERINGS, ordering)


def driver_career_stats(driver: Driver) -> dict:
    race = Result.objects.filter(driver=driver, session__type=RACE).aggregate(
        starts=Count("id"),
        wins=Count("id", filter=Q(position=1)),
        podiums=Count("id", filter=Q(position__lte=3)),
        fastest_laps=Count("id", filter=Q(fastest_lap_rank=1)),
        grid_poles=Count(
            "id", filter=Q(grid=1, session__round__season__year__lt=POLE_QUALIFYING_FROM_YEAR)
        ),
        points=Sum("points"),
    )
    if not race["starts"]:
        return {
            "starts": None,
            "wins": None,
            "podiums": None,
            "poles": None,
            "fastest_laps": None,
            "points": None,
            "titles": None,
        }
    sprint_points = Result.objects.filter(driver=driver, session__type=SPRINT).aggregate(
        points=Sum("points")
    )["points"]
    qualifying_poles = QualifyingResult.objects.filter(
        driver=driver,
        session__type=QUALIFYING,
        position=1,
        session__round__season__year__gte=POLE_QUALIFYING_FROM_YEAR,
    ).count()
    points = (race["points"] or Decimal(0)) + (sprint_points or Decimal(0))
    return {
        "starts": race["starts"],
        "wins": race["wins"],
        "podiums": race["podiums"],
        "poles": race["grid_poles"] + qualifying_poles,
        "fastest_laps": race["fastest_laps"],
        "points": _number(points),
        "titles": None,
    }


def driver_seasons(driver: Driver) -> list[dict]:
    """Season-by-season table, newest first; teams are the ones on race day."""
    year_field = "session__round__season__year"
    rows = {
        row[year_field]: row
        for row in Result.objects.filter(driver=driver, session__type__in=[RACE, SPRINT])
        .values(year_field)
        .annotate(
            points=Sum("points"),
            wins=Count("id", filter=Q(session__type=RACE, position=1)),
        )
    }
    team_rows = list(
        Result.objects.filter(driver=driver, session__type__in=[RACE, SPRINT])
        .values(year_field, "constructor_id", "constructor__slug", "constructor__name")
        .distinct()
        .order_by(year_field, "constructor__name")
    )
    colors = color_map(set(rows), {r["constructor_id"] for r in team_rows})
    teams: dict[int, list[dict]] = defaultdict(list)
    for row in team_rows:
        year = row[year_field]
        teams[year].append(
            team_ref(
                row["constructor__slug"],
                row["constructor__name"],
                colors.get((year, row["constructor_id"])),
            )
        )
    return [
        {
            "year": year,
            "teams": teams[year],
            "points": _number(rows[year]["points"]),
            "wins": rows[year]["wins"],
            # Final championship position needs the standings module.
            "championship_position": None,
        }
        for year in sorted(rows, reverse=True)
    ]


def driver_last_results(driver: Driver) -> list[dict]:
    results = list(
        Result.objects.filter(driver=driver, session__type=RACE)
        .select_related("session__round__season", "constructor")
        .order_by("-session__round__date", "-session_id")[:LAST_RESULTS_LIMIT]
    )
    colors = color_map(
        {r.session.round.season.year for r in results}, {r.constructor_id for r in results}
    )
    return [
        {
            "year": r.session.round.season.year,
            "round": r.session.round.round,
            "round_name": r.session.round.name,
            "date": r.session.round.date,
            "team": team_ref(
                r.constructor.slug,
                r.constructor.name,
                colors.get((r.session.round.season.year, r.constructor_id)),
            ),
            "grid": r.grid,
            "position": r.position,
            "position_text": r.position_text or None,
            "status": r.status or None,
            "points": _number(r.points),
        }
        for r in results
    ]


# --- Constructors ----------------------------------------------------------------------------


def constructor_list(
    *,
    season: int | None = None,
    nationality: str | None = None,
    q: str | None = None,
    ordering: str = "name",
) -> QuerySet:
    race = Q(results__session__type=RACE)
    queryset = Constructor.objects.annotate(
        starts=Count("results__session", filter=race, distinct=True),
        wins=Count("results", filter=race & Q(results__position=1)),
    )
    if season is not None:
        queryset = queryset.filter(
            Exists(
                Result.objects.filter(
                    constructor=OuterRef("pk"), session__round__season__year=season
                )
            )
        )
    if nationality:
        queryset = queryset.filter(nationality__iexact=nationality)
    if q:
        queryset = queryset.filter(name__icontains=q.strip())
    return _ordered(queryset, CONSTRUCTOR_ORDERINGS, ordering)


def constructor_career_stats(constructor: Constructor) -> dict:
    race = Result.objects.filter(constructor=constructor, session__type=RACE).aggregate(
        starts=Count("session", distinct=True),
        wins=Count("session", distinct=True, filter=Q(position=1)),
        podiums=Count("id", filter=Q(position__lte=3)),
        fastest_laps=Count("id", filter=Q(fastest_lap_rank=1)),
        grid_poles=Count(
            "session",
            distinct=True,
            filter=Q(grid=1, session__round__season__year__lt=POLE_QUALIFYING_FROM_YEAR),
        ),
        points=Sum("points"),
    )
    if not race["starts"]:
        return {
            "starts": None,
            "wins": None,
            "podiums": None,
            "poles": None,
            "fastest_laps": None,
            "points": None,
            "titles": None,
        }
    sprint_points = Result.objects.filter(constructor=constructor, session__type=SPRINT).aggregate(
        points=Sum("points")
    )["points"]
    qualifying_poles = (
        QualifyingResult.objects.filter(
            constructor=constructor,
            session__type=QUALIFYING,
            position=1,
            session__round__season__year__gte=POLE_QUALIFYING_FROM_YEAR,
        )
        .values("session")
        .distinct()
        .count()
    )
    points = (race["points"] or Decimal(0)) + (sprint_points or Decimal(0))
    return {
        "starts": race["starts"],
        "wins": race["wins"],
        "podiums": race["podiums"],
        "poles": race["grid_poles"] + qualifying_poles,
        "fastest_laps": race["fastest_laps"],
        "points": _number(points),
        "titles": None,
    }


def constructor_seasons(constructor: Constructor) -> tuple[list[dict], list[dict], int | None]:
    """Return (season table newest first, drivers of the latest season, latest season year)."""
    year_field = "session__round__season__year"
    base = Result.objects.filter(constructor=constructor, session__type__in=[RACE, SPRINT])
    rows = {
        row[year_field]: row
        for row in base.values(year_field).annotate(
            points=Sum("points"),
            wins=Count("session", distinct=True, filter=Q(session__type=RACE, position=1)),
        )
    }
    driver_rows = list(
        base.values(
            year_field,
            "driver__slug",
            "driver__given_name",
            "driver__family_name",
            "driver__code",
            "driver__permanent_number",
        )
        .distinct()
        .order_by(year_field, "driver__family_name", "driver__given_name")
    )
    colors = dict(
        ConstructorSeason.objects.filter(constructor=constructor).values_list(
            "season__year", "color_hex"
        )
    )
    drivers: dict[int, list[dict]] = defaultdict(list)
    for row in driver_rows:
        drivers[row[year_field]].append(
            {
                "slug": row["driver__slug"],
                "name": f"{row['driver__given_name']} {row['driver__family_name']}",
                "code": row["driver__code"] or None,
                "number": row["driver__permanent_number"],
            }
        )
    table = [
        {
            "year": year,
            "color": colors.get(year),
            "points": _number(rows[year]["points"]),
            "wins": rows[year]["wins"],
            "drivers": drivers[year],
            # Constructors' championship position needs the standings module.
            "championship_position": None,
        }
        for year in sorted(rows, reverse=True)
    ]
    latest = max(rows) if rows else None
    return table, (drivers[latest] if latest else []), latest


# --- Circuits --------------------------------------------------------------------------------


def circuit_list(
    *, country: str | None = None, q: str | None = None, ordering: str = "name"
) -> QuerySet:
    held = Q(rounds__is_cancelled=False, rounds__date__lte=timezone.localdate())
    queryset = Circuit.objects.annotate(
        gp_count=Count("rounds", filter=held),
        last_gp_date=Max("rounds__date", filter=held),
    )
    if country:
        queryset = queryset.filter(country__iexact=country)
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q.strip())
            | Q(locality__icontains=q.strip())
            | Q(country__icontains=q.strip())
        )
    return _ordered(queryset, CIRCUIT_ORDERINGS, ordering)


def circuit_with_counts(slug: str) -> Circuit | None:
    return circuit_list().filter(slug=slug).first()


def circuit_winners(circuit: Circuit) -> list[dict]:
    results = list(
        Result.objects.filter(session__round__circuit=circuit, session__type=RACE, position=1)
        .select_related("session__round__season", "driver", "constructor")
        .order_by("-session__round__date")
    )
    colors = color_map(
        {r.session.round.season.year for r in results}, {r.constructor_id for r in results}
    )
    return [
        {
            "year": r.session.round.season.year,
            "round": r.session.round.round,
            "round_name": r.session.round.name,
            "date": r.session.round.date,
            "driver": driver_ref(r.driver),
            "team": team_ref(
                r.constructor.slug,
                r.constructor.name,
                colors.get((r.session.round.season.year, r.constructor_id)),
            ),
        }
        for r in results
    ]


def most_wins(winners: list[dict], key: str) -> list[dict]:
    """Drivers or teams ("driver" / "team") with the most wins on a circuit (ties included)."""
    counts: dict[str, list] = {}
    for winner in winners:
        ref = winner[key]
        entry = counts.setdefault(ref["slug"], [ref, 0])
        entry[1] += 1
    if not counts:
        return []
    top = max(count for _, count in counts.values())
    return [{**ref, "wins": count} for ref, count in counts.values() if count == top]


def driver_ref(driver: Driver) -> dict:
    return {
        "slug": driver.slug,
        "name": f"{driver.given_name} {driver.family_name}",
        "code": driver.code or None,
        "number": driver.permanent_number,
    }


# --- Seasons and rounds ----------------------------------------------------------------------


def season_list() -> QuerySet:
    return Season.objects.annotate(
        rounds_count=Count("rounds", distinct=True),
        cancelled_rounds=Count("rounds", distinct=True, filter=Q(rounds__is_cancelled=True)),
        sprint_rounds=Count("rounds", distinct=True, filter=Q(rounds__sessions__type=SPRINT)),
    ).order_by("-year")


def season_calendar(season: Season) -> list[dict]:
    rounds = list(
        Round.objects.filter(season=season)
        .select_related("circuit")
        .annotate(
            has_sprint=Exists(Session.objects.filter(round=OuterRef("pk"), type=SPRINT)),
        )
        .order_by("date", "round")
    )
    winners = {
        r.session.round_id: r
        for r in Result.objects.filter(
            session__round__season=season, session__type=RACE, position=1
        ).select_related("driver", "constructor", "session")
    }
    colors = season_colors(season.year)
    calendar = []
    for rnd in rounds:
        win = winners.get(rnd.pk)
        calendar.append(
            {
                "round": rnd.round,
                "name": rnd.name,
                "date": rnd.date,
                "is_cancelled": rnd.is_cancelled,
                "has_sprint": rnd.has_sprint,
                "circuit": {
                    "slug": rnd.circuit.slug,
                    "name": rnd.circuit.name,
                    "country": rnd.circuit.country or None,
                },
                "winner": None
                if win is None
                else {
                    "driver": driver_ref(win.driver),
                    "team": team_ref(
                        win.constructor.slug,
                        win.constructor.name,
                        colors.get(win.constructor_id),
                    ),
                },
            }
        )
    return calendar


def round_detail(round_: Round) -> dict:
    sessions = list(
        round_.sessions.annotate(
            has_results=Exists(Result.objects.filter(session=OuterRef("pk")))
            | Exists(QualifyingResult.objects.filter(session=OuterRef("pk")))
        ).order_by(F("start_utc").asc(nulls_last=True), "type")
    )
    siblings = Round.objects.filter(season_id=round_.season_id, round__isnull=False)
    previous = siblings.filter(round__lt=round_.round).order_by("-round").first()
    following = siblings.filter(round__gt=round_.round).order_by("round").first()
    return {
        "year": round_.season.year,
        "round": round_.round,
        "name": round_.name,
        "date": round_.date,
        "is_cancelled": round_.is_cancelled,
        "scheduled_laps": round_.scheduled_laps,
        "circuit": {
            "slug": round_.circuit.slug,
            "name": round_.circuit.name,
            "country": round_.circuit.country or None,
            "locality": round_.circuit.locality or None,
            "length_m": round_.circuit.length_m,
        },
        "sessions": [
            {
                "type": s.type,
                "status": s.status,
                "start_utc": s.start_utc,
                "has_results": s.has_results,
            }
            for s in sessions
        ],
        "previous_round": _round_link(round_.season.year, previous),
        "next_round": _round_link(round_.season.year, following),
    }


def _round_link(year: int, round_: Round | None) -> dict | None:
    if round_ is None:
        return None
    return {"year": year, "round": round_.round, "name": round_.name}


def session_results(round_: Round, session: Session) -> list[dict]:
    colors = season_colors(round_.season.year)

    def team(result):
        return team_ref(
            result.constructor.slug, result.constructor.name, colors.get(result.constructor_id)
        )

    if session.type == QUALIFYING:
        rows = list(
            QualifyingResult.objects.filter(session=session).select_related("driver", "constructor")
        )
        has_q2 = any(r.q2_ms is not None for r in rows)
        has_q3 = any(r.q3_ms is not None for r in rows)
        return [
            {
                "position": r.position,
                "driver": driver_ref(r.driver),
                "team": team(r),
                "q1_ms": r.q1_ms,
                "q2_ms": r.q2_ms,
                "q3_ms": r.q3_ms,
                "eliminated_in": _eliminated_in(r, has_q2, has_q3),
            }
            for r in rows
        ]
    rows = list(Result.objects.filter(session=session).select_related("driver", "constructor"))
    return [
        {
            "position": r.position,
            "position_text": r.position_text or None,
            "driver": driver_ref(r.driver),
            "team": team(r),
            "grid": r.grid,
            "laps": r.laps,
            "status": r.status or None,
            "time_ms": r.time_ms,
            "best_lap_ms": r.best_lap_ms,
            "points": _number(r.points),
            "fastest_lap": None if r.fastest_lap_rank is None else r.fastest_lap_rank == 1,
            "position_change": _position_change(r.grid, r.position),
        }
        for r in rows
    ]


def _position_change(grid: int | None, position: int | None) -> int | None:
    # Grid 0 means a pit-lane start; positive values mean places gained.
    if not grid or position is None:
        return None
    return grid - position


def _eliminated_in(result: QualifyingResult, has_q2: bool, has_q3: bool) -> str | None:
    if has_q3 and result.q3_ms is None and result.q2_ms is not None:
        return "Q2"
    if has_q2 and result.q2_ms is None and result.q1_ms is not None:
        return "Q1"
    return None


# --- Search ----------------------------------------------------------------------------------


def search(query: str) -> dict:
    """Diacritics- and case-insensitive search, at most SEARCH_GROUP_LIMIT hits per group."""
    needle = make_search_name(query)
    drivers = [
        driver_ref(d) | {"nationality": d.nationality or None}
        for d in Driver.objects.filter(search_name__contains=needle).order_by(
            "family_name", "given_name"
        )[:SEARCH_GROUP_LIMIT]
    ]
    # Constructors, circuits and rounds have no normalised name column, so match their (small)
    # tables in Python instead of with a database extension.
    constructors = [
        {"slug": slug, "name": name, "nationality": nationality or None}
        for slug, name, nationality in Constructor.objects.order_by("name").values_list(
            "slug", "name", "nationality"
        )
        if needle in make_search_name(name)
    ][:SEARCH_GROUP_LIMIT]
    circuits = [
        {"slug": slug, "name": name, "country": country or None}
        for slug, name, locality, country in Circuit.objects.order_by("name").values_list(
            "slug", "name", "locality", "country"
        )
        if needle in make_search_name(name, locality)
    ][:SEARCH_GROUP_LIMIT]
    rounds = []
    for year, number, name, date, circuit_name in (
        Round.objects.filter(round__isnull=False)
        .order_by("-date")
        .values_list("season__year", "round", "name", "date", "circuit__name")
    ):
        if needle in make_search_name(name, circuit_name):
            rounds.append({"year": year, "round": number, "name": name, "date": date})
            if len(rounds) == SEARCH_GROUP_LIMIT:
                break
    return {
        "drivers": drivers,
        "constructors": constructors,
        "circuits": circuits,
        "rounds": rounds,
    }


# --- Public functions for the predictions module (it may not import catalog models) ----------


def find_round(year: int, number: int) -> dict | None:
    """Identify a round by season year and round number: id, year, round, name, is_cancelled."""
    row = (
        Round.objects.filter(season__year=year, round=number)
        .values("id", "season__year", "round", "name", "is_cancelled")
        .first()
    )
    if row is None:
        return None
    return {
        "id": row["id"],
        "year": row["season__year"],
        "round": row["round"],
        "name": row["name"],
        "is_cancelled": row["is_cancelled"],
    }


def round_refs(round_ids) -> dict[int, dict]:
    """Map round id to {id, year, round, name} for the given ids (one query)."""
    rows = Round.objects.filter(id__in=list(round_ids)).values(
        "id", "season__year", "round", "name"
    )
    return {
        row["id"]: {
            "id": row["id"],
            "year": row["season__year"],
            "round": row["round"],
            "name": row["name"],
        }
        for row in rows
    }


def session_info(session_id: int) -> dict | None:
    """Return {id, type, round_id} of a session, or None when it does not exist."""
    row = Session.objects.filter(id=session_id).values("id", "type", "round_id").first()
    return dict(row) if row else None


def qualifying_start(round_id: int):
    """Start (UTC datetime) of the qualifying session of a round, or None when unknown."""
    return (
        Session.objects.filter(round_id=round_id, type=QUALIFYING)
        .values_list("start_utc", flat=True)
        .first()
    )


def existing_driver_ids(driver_ids) -> set[int]:
    """Subset of the given ids that are real drivers."""
    return set(Driver.objects.filter(id__in=list(driver_ids)).values_list("id", flat=True))


def driver_labels(driver_ids) -> dict[int, dict]:
    """Map driver id to {id, name, code} (one query)."""
    rows = Driver.objects.filter(id__in=list(driver_ids)).values(
        "id", "given_name", "family_name", "code"
    )
    return {
        row["id"]: {
            "id": row["id"],
            "name": f"{row['given_name']} {row['family_name']}".strip(),
            "code": row["code"] or None,
        }
        for row in rows
    }


def race_outcomes(round_ids) -> dict[int, dict]:
    """What the predictions game scores against, per round id, with None for missing pieces.

    Each value is {"podium": [p1, p2, p3], "pole": id, "fastest_lap": id} of driver ids.
    Disqualified drivers (position_text "D") do not count. Pole comes from the qualifying
    classification and falls back to grid == 1 of the race when there is none. Two queries.
    """
    ids = list(round_ids)
    outcomes = {
        round_id: {"podium": [None, None, None], "pole": None, "fastest_lap": None}
        for round_id in ids
    }
    grid_pole: dict[int, int] = {}
    race = (
        Result.objects.filter(session__round_id__in=ids, session__type=RACE)
        .exclude(position_text="D")
        .values_list("session__round_id", "driver_id", "position", "grid", "fastest_lap_rank")
    )
    for round_id, driver_id, position, grid, rank in race:
        outcome = outcomes[round_id]
        if position in (1, 2, 3):
            outcome["podium"][position - 1] = driver_id
        if rank == 1:
            outcome["fastest_lap"] = driver_id
        if grid == 1:
            grid_pole[round_id] = driver_id
    qualifying = dict(
        QualifyingResult.objects.filter(
            session__round_id__in=ids, session__type=QUALIFYING, position=1
        ).values_list("session__round_id", "driver_id")
    )
    for round_id, outcome in outcomes.items():
        outcome["pole"] = qualifying.get(round_id) or grid_pole.get(round_id)
    return outcomes


def race_outcome(round_id: int) -> dict:
    """Single-round form of `race_outcomes`."""
    return race_outcomes([round_id])[round_id]

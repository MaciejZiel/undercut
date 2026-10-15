"""Read queries of the catalog module.

Everything the public read API needs lives here so views stay thin. Missing data is returned as
None (never as zero); counts are real counts of stored rows.

Conventions:
- "starts", "wins", "podiums" and "fastest laps" are counted over RACE sessions only.
- "points" add RACE and SPRINT sessions.
- Pole positions come from grid == 1 on race sessions before POLE_QUALIFYING_FROM_YEAR and from
  qualifying position 1 afterwards.
- Titles come from the standings module's selectors (position 1 after the last round of a
  finished season); they are never derived here.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.utils import timezone

from apps.standings import selectors as standings

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
SPRINT_QUALIFYING = Session.Type.SQ
PRACTICE = (Session.Type.FP1, Session.Type.FP2, Session.Type.FP3)

DRIVER_ORDERINGS = {
    "family_name": ("family_name", "given_name"),
    "wins": ("wins", "family_name"),
    "starts": ("starts", "family_name"),
    "titles": ("titles", "family_name", "given_name"),
}
CONSTRUCTOR_ORDERINGS = {
    "name": ("name",),
    "wins": ("wins", "name"),
    "starts": ("starts", "name"),
    "titles": ("titles", "name"),
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


def _titles_annotation(counts: dict[int, int]):
    """Per-row title count as SQL (a CASE over the few champions), so it can be sorted on."""
    if not counts:
        return Value(0, output_field=IntegerField())
    return Case(
        *[When(pk=pk, then=Value(n)) for pk, n in counts.items()],
        default=Value(0),
        output_field=IntegerField(),
    )


def latest_result_year() -> int | None:
    return Result.objects.aggregate(year=Max("session__round__season__year"))["year"]


# --- Drivers ---------------------------------------------------------------------------------


def driver_list(
    *,
    season: int | None = None,
    nationality: str | None = None,
    constructor: str | None = None,
    active: bool | None = None,
    champion: bool | None = None,
    q: str | None = None,
    ordering: str = "family_name",
    with_titles: bool = True,
) -> QuerySet:
    """Drivers with counters. `with_titles=False` skips the standings lookup (titles = 0)."""
    race = Q(results__session__type=RACE)
    titles = standings.title_counts("drivers") if with_titles else {}
    last_race = Result.objects.filter(driver=OuterRef("pk"), session__type=RACE).order_by(
        "-session__round__date", "-session_id"
    )
    queryset = Driver.objects.annotate(
        starts=Count("results", filter=race),
        wins=Count("results", filter=race & Q(results__position=1)),
        titles=_titles_annotation(titles),
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
    if champion is not None:
        queryset = queryset.filter(pk__in=titles) if champion else queryset.exclude(pk__in=titles)
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


def driver_title_summary(driver: Driver) -> dict:
    """{"titles": n, "positions": {year: position}} of one driver (one query)."""
    return standings.entity_summary("drivers", driver.pk)


def driver_career_stats(driver: Driver, summary: dict | None = None) -> dict:
    """Career totals; `summary` may carry a precomputed `driver_title_summary(driver)`."""
    if summary is None:
        summary = driver_title_summary(driver)
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
        "titles": summary["titles"],
    }


def driver_seasons(driver: Driver, summary: dict | None = None) -> list[dict]:
    """Season-by-season table, newest first; teams are the ones on race day."""
    if summary is None:
        summary = driver_title_summary(driver)
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
    positions = summary["positions"]
    return [
        {
            "year": year,
            "teams": teams[year],
            "points": _number(rows[year]["points"]),
            "wins": rows[year]["wins"],
            "championship_position": positions.get(year),
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
        titles=_titles_annotation(standings.title_counts("constructors")),
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


def constructor_title_summary(constructor: Constructor) -> dict:
    """{"titles": n, "positions": {year: position}} of one constructor (one query)."""
    return standings.entity_summary("constructors", constructor.pk)


def constructor_career_stats(constructor: Constructor, summary: dict | None = None) -> dict:
    if summary is None:
        summary = constructor_title_summary(constructor)
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
        "titles": summary["titles"],
    }


def constructor_seasons(
    constructor: Constructor, summary: dict | None = None
) -> tuple[list[dict], list[dict], int | None]:
    """Return (season table newest first, drivers of the latest season, latest season year)."""
    if summary is None:
        summary = constructor_title_summary(constructor)
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
    positions = summary["positions"]
    table = [
        {
            "year": year,
            "color": colors.get(year),
            "points": _number(rows[year]["points"]),
            "wins": rows[year]["wins"],
            "drivers": drivers[year],
            "championship_position": positions.get(year),
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


def circuit_lap_record(circuit: Circuit) -> dict | None:
    """The fastest race lap on record here. A hand-entered record on the circuit wins.

    Derived from the fastest-lap result of every race held on the circuit (Jolpica has them from
    2004). Layouts change over the years, so the year is part of the answer.
    """
    if circuit.lap_record_ms:
        return {
            "time_ms": circuit.lap_record_ms,
            "driver": circuit.lap_record_driver or None,
            "year": circuit.lap_record_year,
        }
    best = (
        Result.objects.filter(
            session__round__circuit=circuit,
            session__type=RACE,
            fastest_lap_rank=1,
            best_lap_ms__isnull=False,
        )
        .select_related("driver", "session__round__season")
        .order_by("best_lap_ms", "-session__round__date")
        .first()
    )
    if best is None:
        return None
    return {
        "time_ms": best.best_lap_ms,
        "driver": f"{best.driver.given_name} {best.driver.family_name}",
        "year": best.session.round.season.year,
    }


def circuit_length(circuit: Circuit) -> tuple[int | None, bool]:
    """(metres, is_estimate). The length measured on the outline is rounded to 100 m."""
    if circuit.length_m:
        return circuit.length_m, False
    measured = (circuit.outline or {}).get("length_m")
    return (round(measured / 100) * 100, True) if measured else (None, False)


def circuit_outline(circuit: Circuit) -> dict | None:
    outline = circuit.outline
    if not outline or not outline.get("points"):
        return None
    return {
        "width": outline["width"],
        "height": outline["height"],
        "points": outline["points"],
        # Outlines drawn from one OpenF1 lap know where the start line is; the others do not say.
        "marker": outline.get("marker", True),
        "origin": outline.get("origin", "openf1"),
    }


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
            "length_m": circuit_length(round_.circuit)[0],
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

    if session.type in PRACTICE:
        return _practice_results(session, team)
    if session.type in (QUALIFYING, SPRINT_QUALIFYING):
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
                "eliminated_in": _eliminated_in(r, has_q2, has_q3, session.type),
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


def _eliminated_in(
    result: QualifyingResult, has_q2: bool, has_q3: bool, session_type: str = QUALIFYING
) -> str | None:
    prefix = "SQ" if session_type == SPRINT_QUALIFYING else "Q"
    if has_q3 and result.q3_ms is None and result.q2_ms is not None:
        return f"{prefix}2"
    if has_q2 and result.q2_ms is None and result.q1_ms is not None:
        return f"{prefix}1"
    return None


def _practice_results(session: Session, team) -> list[dict]:
    """Practice classification: best lap, gap to the fastest car and laps driven."""
    rows = list(
        Result.objects.filter(session=session)
        .select_related("driver", "constructor")
        .order_by(F("position").asc(nulls_last=True), "driver_id")
    )
    leader = next((r.best_lap_ms for r in rows if r.best_lap_ms), None)
    return [
        {
            "position": r.position,
            "driver": driver_ref(r.driver),
            "team": team(r),
            "laps": r.laps,
            "best_lap_ms": r.best_lap_ms,
            "gap_ms": None if r.best_lap_ms is None or leader is None else r.best_lap_ms - leader,
        }
        for r in rows
    ]


# --- Search ----------------------------------------------------------------------------------


def _word_start_first(needle: str, rows: list, text) -> list:
    """Matches where the needle begins a word come before those where it sits inside one."""
    return sorted(rows, key=lambda row: not any(w.startswith(needle) for w in text(row).split()))


def _year_span(first: int | None, last: int | None) -> str | None:
    if first is None or last is None:
        return None
    return str(first) if first == last else f"{first}\u2013{last}"


def search(query: str) -> dict:
    """Diacritics- and case-insensitive search, at most SEARCH_GROUP_LIMIT hits per group."""
    needle = make_search_name(query)
    # The ones with the most starts first, so "lecl" finds Charles before a driver of 1950.
    found = (
        Driver.objects.filter(search_name__contains=needle)
        .annotate(
            starts=Count("results"),
            first_year=Min("results__session__round__season__year"),
            last_year=Max("results__session__round__season__year"),
        )
        .annotate(
            word_start=Case(
                When(
                    Q(search_name__startswith=needle) | Q(search_name__contains=f" {needle}"),
                    then=0,
                ),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("word_start", "-starts", "family_name", "given_name")[:SEARCH_GROUP_LIMIT]
    )
    drivers = [
        driver_ref(d)
        | {
            "nationality": d.nationality or None,
            "years": _year_span(getattr(d, "first_year", None), getattr(d, "last_year", None)),
        }
        for d in found
    ]
    # Constructors, circuits and rounds have no normalised name column, so match their (small)
    # tables in Python instead of with a database extension.
    constructors = [
        {"slug": slug, "name": name, "nationality": nationality or None}
        for slug, name, nationality in Constructor.objects.order_by("name").values_list(
            "slug", "name", "nationality"
        )
        if needle in make_search_name(name)
    ]
    constructors = _word_start_first(needle, constructors, lambda c: make_search_name(c["name"]))[
        :SEARCH_GROUP_LIMIT
    ]
    circuits = [
        {"slug": slug, "name": name, "country": country or None}
        for slug, name, locality, country in Circuit.objects.order_by("name").values_list(
            "slug", "name", "locality", "country"
        )
        if needle in make_search_name(name, locality)
    ]
    circuits = _word_start_first(needle, circuits, lambda c: make_search_name(c["name"]))[
        :SEARCH_GROUP_LIMIT
    ]
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


# --- Champions on the season list ------------------------------------------------------------


def season_champions(years) -> dict[int, dict]:
    """Year -> {"driver_champion": driver ref or None, "constructor_champion": team ref or None}.

    Champions come from the standings selectors (finished seasons only). Five queries.
    """
    wanted = set(years)
    driver_champs = {y: i for y, i in standings.champions("drivers").items() if y in wanted}
    team_champs = {y: i for y, i in standings.champions("constructors").items() if y in wanted}
    drivers = Driver.objects.in_bulk(set(driver_champs.values()))
    teams = Constructor.objects.in_bulk(set(team_champs.values()))
    colors = color_map(team_champs, team_champs.values()) if team_champs else {}
    result = {}
    for year in driver_champs.keys() | team_champs.keys():
        team = teams.get(team_champs.get(year))
        driver = drivers.get(driver_champs.get(year))
        result[year] = {
            "driver_champion": None if driver is None else driver_ref(driver),
            "constructor_champion": None
            if team is None
            else team_ref(team.slug, team.name, colors.get((year, team.pk))),
        }
    return result


# --- Calendar (FR-102) -----------------------------------------------------------------------

RACE_OVER_AFTER = timedelta(hours=4)  # a race that started this long ago counts as completed
FINAL_STATUSES = (Session.Status.FINISHED, Session.Status.RESULTS_FINAL)


def calendar_year() -> int | None:
    """The current season: the latest one that has rounds."""
    return (
        Season.objects.filter(rounds__isnull=False)
        .order_by("-year")
        .values_list("year", flat=True)
        .first()
    )


def _is_completed(rnd: Round, race: Session | None, has_winner: bool, now: dt.datetime) -> bool:
    if has_winner or (race is not None and race.status in FINAL_STATUSES):
        return True
    if race is not None and race.start_utc is not None:
        return race.start_utc + RACE_OVER_AFTER <= now
    day_after = dt.datetime.combine(rnd.date + timedelta(days=1), dt.time.min, dt.UTC)
    return day_after <= now


def calendar(year: int, now: dt.datetime | None = None) -> dict:
    """Every round of a season with sessions, circuit and a status label. Five queries.

    Status is "cancelled", "completed" (race finished, has a winner, or started over four hours
    ago), "next" (the first round that is not completed; it also covers a race in progress) or
    "upcoming". `race_start_utc` is the countdown target.
    """
    now = now or timezone.now()
    rounds = list(
        Round.objects.filter(season__year=year)
        .select_related("circuit")
        .prefetch_related("sessions")
        .order_by("date", "round")
    )
    winners = {
        r.session.round_id: r
        for r in Result.objects.filter(
            session__round__season__year=year, session__type=RACE, position=1
        ).select_related("driver", "constructor", "session")
    }
    colors = season_colors(year)
    entries = []
    next_found = False
    for rnd in rounds:
        sessions = sorted(
            rnd.sessions.all(),
            key=lambda s: (s.start_utc is None, s.start_utc or now, s.type),
        )
        race = next((s for s in sessions if s.type == RACE), None)
        win = winners.get(rnd.pk)
        if rnd.is_cancelled:
            status = "cancelled"
        elif _is_completed(rnd, race, win is not None, now):
            status = "completed"
        elif not next_found:
            status, next_found = "next", True
        else:
            status = "upcoming"
        entries.append(
            {
                "round": rnd.round,
                "name": rnd.name,
                "date": rnd.date,
                "status": status,
                "is_next": status == "next",
                "has_sprint": any(s.type == SPRINT for s in sessions),
                "race_start_utc": None if race is None else race.start_utc,
                "circuit": {
                    "slug": rnd.circuit.slug,
                    "name": rnd.circuit.name,
                    "country": rnd.circuit.country or None,
                    "locality": rnd.circuit.locality or None,
                    "timezone": rnd.circuit.timezone or None,
                },
                "sessions": [
                    {
                        "type": s.type,
                        "start_utc": s.start_utc,
                        "end_utc": s.end_utc,
                        "status": s.status,
                    }
                    for s in sessions
                ],
                "winner": None
                if win is None
                else {
                    "driver": driver_ref(win.driver),
                    "team": team_ref(
                        win.constructor.slug, win.constructor.name, colors.get(win.constructor_id)
                    ),
                },
            }
        )
    next_entry = next((e for e in entries if e["is_next"]), None)
    return {
        "year": year,
        "next_round": None
        if next_entry is None
        else {
            "round": next_entry["round"],
            "name": next_entry["name"],
            "race_start_utc": next_entry["race_start_utc"],
        },
        "rounds": entries,
    }


# --- Dashboard (FR-105, FR-106) --------------------------------------------------------------

DASHBOARD_TOP = 5


def _podium_entry(result: Result, colors: dict) -> dict:
    return {
        "position": result.position,
        "driver": driver_ref(result.driver),
        "team": team_ref(
            result.constructor.slug,
            result.constructor.name,
            colors.get(result.constructor_id),
        ),
    }


def last_completed_race() -> dict | None:
    """Newest race with results: podium (top 3, team on race day) and fastest lap. Two queries
    plus one for colours."""
    latest = (
        Result.objects.filter(session__type=RACE)
        .order_by("-session__round__date", "-session_id")
        .values_list(
            "session_id",
            "session__round__season__year",
            "session__round__round",
            "session__round__name",
            "session__round__date",
            "session__round__circuit__slug",
            "session__round__circuit__name",
            "session__round__circuit__country",
        )
        .first()
    )
    if latest is None:
        return None
    session_id, year, number, name, date, circuit_slug, circuit_name, country = latest
    rows = list(
        Result.objects.filter(session_id=session_id)
        .filter(Q(position__lte=3) | Q(fastest_lap_rank=1))
        .select_related("driver", "constructor")
        .order_by(F("position").asc(nulls_last=True))
    )
    colors = season_colors(year)
    fastest = next((r for r in rows if r.fastest_lap_rank == 1), None)
    return {
        "year": year,
        "round": number,
        "name": name,
        "date": date,
        "circuit": {"slug": circuit_slug, "name": circuit_name, "country": country or None},
        "podium": [
            _podium_entry(r, colors) for r in rows if r.position is not None and r.position <= 3
        ],
        "fastest_lap": None
        if fastest is None
        else {
            "driver": driver_ref(fastest.driver),
            "team": _podium_entry(fastest, colors)["team"],
            "time_ms": fastest.best_lap_ms,
        },
    }


def _top_standings(kind: str) -> dict:
    latest = standings.latest_position(kind)
    if latest is None:
        return {"season": None, "after_round": None, "entries": []}
    rows = standings.standings_rows(kind, latest.season_id, latest.after_round)[:DASHBOARD_TOP]
    colors = season_colors(latest.year)
    teams = (
        _drivers_teams(latest.year, [r["entity"]["id"] for r in rows]) if kind == "drivers" else {}
    )
    entries = []
    for row in rows:
        entity_id = row["entity"]["id"]
        if kind == "constructors":
            color, team_name = colors.get(entity_id), None
        else:
            constructor_id, team_name = teams.get(entity_id, (None, None))
            color = colors.get(constructor_id) if constructor_id is not None else None
        entries.append(
            {
                "position": row["position"],
                "slug": row["entity"]["slug"],
                "name": row["entity"]["name"],
                "code": row["entity"]["code"],
                "color": color,
                "team_name": team_name,
                "points": row["points"],
                "wins": row["wins"],
            }
        )
    return {"season": latest.year, "after_round": latest.after_round, "entries": entries}


def _drivers_teams(year: int, driver_ids: list[int]) -> dict[int, tuple[int, str]]:
    """driver id -> (constructor id, name) from each driver's latest result that season."""
    latest: dict[int, tuple[int, str]] = {}
    results = (
        Result.objects.filter(driver_id__in=driver_ids, session__round__season__year=year)
        .select_related("constructor")
        .order_by("-session__round__date", "-session_id")
    )
    for result in results:
        latest.setdefault(result.driver_id, (result.constructor_id, result.constructor.name))
    return latest


def standings_colors(kind: str, year: int, entity_ids: list[int]) -> dict[int, dict]:
    """Colour and team name for championship entries, keyed by driver or constructor id.

    A driver takes the colour of the team of their latest result that season; a constructor its own.
    Entries without a known colour map to None. Two queries.
    """
    colors = season_colors(year)
    if kind == "constructors":
        return {i: {"color": colors.get(i), "team_name": None} for i in entity_ids}
    teams = _drivers_teams(year, entity_ids)
    out: dict[int, dict] = {}
    for i in entity_ids:
        constructor_id, team_name = teams.get(i, (None, None))
        color = colors.get(constructor_id) if constructor_id is not None else None
        out[i] = {"color": color, "team_name": team_name}
    return out


def this_day_in_f1(today: dt.date) -> dict | None:
    """A race won on today's day and month in an earlier year.

    The pick is deterministic: candidates are ordered by date and the one at index
    `today.toordinal() % len(candidates)` is taken, so it changes daily but is stable within a
    day. Two queries.
    """
    candidates = list(
        Result.objects.filter(
            session__type=RACE,
            position=1,
            session__round__is_cancelled=False,
            session__round__date__month=today.month,
            session__round__date__day=today.day,
            session__round__date__year__lt=today.year,
        )
        .select_related("driver", "constructor", "session__round")
        .order_by("session__round__date", "session_id")
    )
    if not candidates:
        return None
    pick = candidates[today.toordinal() % len(candidates)]
    rnd = pick.session.round
    year = rnd.date.year
    colors = color_map({year}, {pick.constructor_id})
    return {
        "year": year,
        "round": rnd.round,
        "race": rnd.name,
        "date": rnd.date,
        "driver": driver_ref(pick.driver),
        "team": team_ref(
            pick.constructor.slug, pick.constructor.name, colors.get((year, pick.constructor_id))
        ),
    }


def dashboard(now: dt.datetime | None = None) -> dict:
    """Everything the home page needs; every part is null or empty on an empty database."""
    now = now or timezone.now()
    year = calendar_year()
    next_race = None
    if year is not None:
        entry = next((e for e in calendar(year, now)["rounds"] if e["is_next"]), None)
        if entry is not None:
            next_race = {"year": year, **entry}
    today = now.date()
    return {
        "next_race": next_race,
        "last_race": last_completed_race(),
        "driver_standings": _top_standings("drivers"),
        "constructor_standings": _top_standings("constructors"),
        "this_day_in_f1": this_day_in_f1(today),
        "counts": {
            "seasons": Season.objects.count(),
            "races": Round.objects.filter(is_cancelled=False, date__lte=today).count(),
            "drivers": Driver.objects.count(),
        },
    }


# --- Compare (FR-405) ------------------------------------------------------------------------

NOT_CLASSIFIED = {"R", "D", "W", "F", "N", "E"}
SAME_TEAM_LAP_COMPARISON_FROM = 2023


def _classified(position: int | None, position_text: str) -> bool:
    return position is not None and position_text not in NOT_CLASSIFIED


def head_to_head(a: Driver, b: Driver, year: int | None = None) -> dict:
    """Head-to-head of two drivers over races both entered (three queries).

    Race: both classified, the better finishing position is ahead. Qualifying: qualifying
    position from POLE_QUALIFYING_FROM_YEAR (1994), grid position (pit lane 0 ignored) before.
    `teammate_seasons` lists seasons from 2023 in which both raced for the same constructor.
    """
    race_rows = Result.objects.filter(session__type=RACE, driver_id__in=[a.pk, b.pk])
    quali_rows = QualifyingResult.objects.filter(
        session__type=QUALIFYING,
        driver_id__in=[a.pk, b.pk],
        session__round__season__year__gte=POLE_QUALIFYING_FROM_YEAR,
    )
    if year is not None:
        race_rows = race_rows.filter(session__round__season__year=year)
        quali_rows = quali_rows.filter(session__round__season__year=year)
    by_round: dict[int, dict[int, tuple]] = defaultdict(dict)
    round_year: dict[int, int] = {}
    for (
        round_id,
        season_year,
        driver_id,
        ctor_id,
        ctor_slug,
        position,
        text,
        grid,
    ) in race_rows.values_list(
        "session__round_id",
        "session__round__season__year",
        "driver_id",
        "constructor_id",
        "constructor__slug",
        "position",
        "position_text",
        "grid",
    ):
        by_round[round_id][driver_id] = (ctor_id, ctor_slug, position, text, grid)
        round_year[round_id] = season_year
    quali: dict[int, dict[int, int | None]] = defaultdict(dict)
    for round_id, driver_id, position in quali_rows.values_list(
        "session__round_id", "driver_id", "position"
    ):
        quali[round_id][driver_id] = position

    together = same_team = 0
    race = {"both_finished": 0, "a_ahead": 0, "b_ahead": 0}
    qualifying = {"compared": 0, "a_ahead": 0, "b_ahead": 0}
    team_years: dict[int, dict[str, int]] = defaultdict(dict)
    for round_id, drivers in by_round.items():
        if a.pk not in drivers or b.pk not in drivers:
            continue
        together += 1
        ra, rb = drivers[a.pk], drivers[b.pk]
        if ra[0] == rb[0]:
            same_team += 1
            seen = team_years[round_year[round_id]]
            seen[ra[1]] = seen.get(ra[1], 0) + 1
        if _classified(ra[2], ra[3]) and _classified(rb[2], rb[3]) and ra[2] != rb[2]:
            race["both_finished"] += 1
            race["a_ahead" if ra[2] < rb[2] else "b_ahead"] += 1
        if round_year[round_id] >= POLE_QUALIFYING_FROM_YEAR:
            qa, qb = quali[round_id].get(a.pk), quali[round_id].get(b.pk)
        else:
            qa, qb = ra[4] or None, rb[4] or None
        if qa is not None and qb is not None and qa != qb:
            qualifying["compared"] += 1
            qualifying["a_ahead" if qa < qb else "b_ahead"] += 1
    teammate_seasons = [
        {"year": season_year, "team_slug": slug, "races": count}
        for season_year, teams in sorted(team_years.items())
        if season_year >= SAME_TEAM_LAP_COMPARISON_FROM
        for slug, count in sorted(teams.items())
    ]
    return {
        "races_together": together,
        "same_team_races": same_team,
        "race": race,
        "qualifying": qualifying,
        "teammate_seasons": teammate_seasons,
    }


def compare_drivers(a: Driver, b: Driver, year: int | None = None) -> dict:
    return {
        "season": year,
        "a": {"driver": driver_ref(a), "stats": driver_career_stats(a)},
        "b": {"driver": driver_ref(b), "stats": driver_career_stats(b)},
        "head_to_head": head_to_head(a, b, year),
    }


# --- Season matrix (FR-304) ------------------------------------------------------------------


def _result_category(position: int | None, text: str, points) -> str:
    if not _classified(position, text):
        return "dnf"
    if position == 1:
        return "win"
    if position <= 3:
        return "podium"
    return "points" if points and points > 0 else "no_points"


def season_matrix(season: Season) -> dict:
    """Drivers x rounds grid of race finishing positions (six queries at most).

    Cells are aligned to `rounds`; None means the driver did not take part. Categories: win,
    podium (2-3), points, no_points (classified outside the points) and dnf (retired,
    disqualified, withdrew or not classified). Drivers are ordered by the newest championship
    table, falling back to race points.
    """
    rounds = list(
        Round.objects.filter(season=season, is_cancelled=False, round__isnull=False)
        .order_by("round")
        .values("round", "name", "date", "circuit__country")
    )
    index = {r["round"]: i for i, r in enumerate(rounds)}
    rows = (
        Result.objects.filter(session__round__season=season, session__type=RACE)
        .order_by("session__round__round")
        .values_list(
            "driver_id",
            "driver__slug",
            "driver__given_name",
            "driver__family_name",
            "driver__code",
            "constructor_id",
            "constructor__slug",
            "constructor__name",
            "session__round__round",
            "position",
            "position_text",
            "points",
        )
    )
    drivers: dict[int, dict] = {}
    for (
        driver_id,
        slug,
        given,
        family,
        code,
        ctor_id,
        ctor_slug,
        ctor_name,
        number,
        position,
        text,
        points,
    ) in rows:
        if number not in index:
            continue
        entry = drivers.setdefault(
            driver_id,
            {
                "slug": slug,
                "name": f"{given} {family}".strip(),
                "code": code or None,
                "family": family,
                "total": Decimal(0),
                "cells": [None] * len(rounds),
                "ctor": None,
            },
        )
        entry["total"] += points
        entry["ctor"] = (ctor_id, ctor_slug, ctor_name)
        entry["cells"][index[number]] = {
            "position": position if _classified(position, text) else None,
            "category": _result_category(position, text, points),
        }
    positions = standings.season_positions("drivers", season.pk)
    colors = season_colors(season.year)
    ordered = sorted(
        drivers.items(),
        key=lambda kv: (
            positions.get(kv[0]) is None,
            positions.get(kv[0]) or 0,
            -kv[1]["total"],
            kv[1]["family"],
        ),
    )
    return {
        "year": season.year,
        "rounds": [
            {
                "round": r["round"],
                "name": r["name"],
                "date": r["date"],
                "country": r["circuit__country"] or None,
            }
            for r in rounds
        ],
        "drivers": [
            {
                "slug": e["slug"],
                "name": e["name"],
                "code": e["code"],
                "position": positions.get(driver_id),
                "points": float(e["total"]),
                "team": team_ref(e["ctor"][1], e["ctor"][2], colors.get(e["ctor"][0])),
                "cells": e["cells"],
            }
            for driver_id, e in ordered
        ],
    }

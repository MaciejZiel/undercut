"""Read side: lookups over imported standings. Catalog data is reached via FK joins only."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from django.db.models import Exists, F, Max, OuterRef, Q, Subquery

from .models import ConstructorStanding, DriverStanding

Kind = Literal["drivers", "constructors"]

_MODELS = {"drivers": DriverStanding, "constructors": ConstructorStanding}
_ENTITY_FIELD = {"drivers": "driver", "constructors": "constructor"}


def _model(kind: Kind):
    return _MODELS[kind]


def entity_data(kind: Kind, entity) -> dict:
    """Display data of a driver or constructor row reached through a ForeignKey."""
    if kind == "drivers":
        return {
            "id": entity.pk,
            "slug": entity.slug,
            "name": f"{entity.given_name} {entity.family_name}".strip(),
            "code": entity.code or None,
            "nationality": entity.nationality or None,
        }
    return {
        "id": entity.pk,
        "slug": entity.slug,
        "name": entity.name,
        "code": None,
        "nationality": entity.nationality or None,
    }


def find_season_id(year: int) -> int | None:
    season_model = DriverStanding._meta.get_field("season").related_model
    return season_model.objects.filter(year=year).values_list("pk", flat=True).first()


@dataclass(frozen=True)
class Latest:
    season_id: int
    year: int
    after_round: int


def latest_position(kind: Kind) -> Latest | None:
    """Newest season, and its newest round, that has any standings data."""
    row = (
        _model(kind)
        .objects.order_by("-season__year", "-after_round")
        .values_list("season_id", "season__year", "after_round")
        .first()
    )
    return Latest(*row) if row else None


def latest_round(kind: Kind, season_id: int) -> int | None:
    return (
        _model(kind)
        .objects.filter(season_id=season_id)
        .order_by("-after_round")
        .values_list("after_round", flat=True)
        .first()
    )


def available_rounds(kind: Kind, season_id: int) -> list[int]:
    return list(
        _model(kind)
        .objects.filter(season_id=season_id)
        .order_by("after_round")
        .values_list("after_round", flat=True)
        .distinct()
    )


def standings_rows(kind: Kind, season_id: int, after_round: int | None = None) -> list[dict]:
    """Table after `after_round` (default: latest round with data), best first.

    Each item carries `gap_to_leader`: points behind the entry with the most points.
    One query, entity joined with select_related.
    """
    if after_round is None:
        after_round = latest_round(kind, season_id)
        if after_round is None:
            return []
    field = _ENTITY_FIELD[kind]
    objs = list(
        _model(kind)
        .objects.filter(season_id=season_id, after_round=after_round)
        .select_related(field)
        .order_by("position", "-points", f"{field}_id")
    )
    leader_points = max((o.points for o in objs), default=Decimal(0))
    return [
        {
            "position": o.position,
            "position_text": o.position_text,
            "entity": entity_data(kind, getattr(o, field)),
            "points": o.points,
            "wins": o.wins,
            "podiums": o.podiums,
            "gap_to_leader": leader_points - o.points,
        }
        for o in objs
    ]


def points_progression(kind: Kind, season_id: int, top: int = 5) -> dict:
    """Per-round cumulative points and position for the `top` entries of the final table.

    Returns {"rounds": [n, ...], "series": [{"entity", "points": [...], "positions": [...]}]}
    where each list is aligned to `rounds` and holds None for rounds without an entry.
    Two queries: the data itself and nothing else (entities are joined).
    """
    field = _ENTITY_FIELD[kind]
    objs = list(
        _model(kind)
        .objects.filter(season_id=season_id)
        .select_related(field)
        .order_by("after_round", "position", "-points", f"{field}_id")
    )
    rounds = sorted({o.after_round for o in objs})
    if not rounds:
        return {"rounds": [], "series": []}
    index = {r: i for i, r in enumerate(rounds)}

    by_entity: dict[int, dict] = {}
    for o in objs:
        entity = getattr(o, field)
        item = by_entity.setdefault(
            entity.pk,
            {
                "entity": entity_data(kind, entity),
                "points": [None] * len(rounds),
                "positions": [None] * len(rounds),
                "_last": -1,
            },
        )
        i = index[o.after_round]
        item["points"][i] = o.points
        item["positions"][i] = o.position
        item["_last"] = max(item["_last"], i)

    def final_rank(item: dict):
        i = item["_last"]
        pos = item["positions"][i]
        # Entries that dropped out earlier rank behind those present in the last round.
        return (-i, pos is None, pos or 0, -item["points"][i])

    ranked = sorted(by_entity.values(), key=final_rank)[:top]
    for item in ranked:
        del item["_last"]
    return {"rounds": rounds, "series": ranked}


# --- Championship titles ---------------------------------------------------------------------

CONSTRUCTORS_TITLES_FROM = 1958  # the constructors' championship started in 1958


def _season_model():
    # Catalog is reached through the ForeignKey, never through an import of its models.
    return DriverStanding._meta.get_field("season").related_model


def champions(kind: Kind) -> dict[int, int]:
    """Season year -> id of the champion (driver or constructor) for finished seasons.

    A season is finished when the table after its last (non-cancelled) round exists and that
    round's race has results. The champion is the entry at position 1 of that table.
    Constructors count from CONSTRUCTORS_TITLES_FROM. Two queries.
    """
    field = _ENTITY_FIELD[kind]
    last_round = dict(
        _season_model()
        .objects.annotate(last=Max("rounds__round", filter=Q(rounds__is_cancelled=False)))
        .filter(last__isnull=False)
        .values_list("year", "last")
    )
    queryset = _model(kind).objects.filter(
        position=1,
        after_round=F("season__rounds__round"),
        season__rounds__sessions__type="RACE",
        season__rounds__sessions__results__isnull=False,
    )
    if kind == "constructors":
        queryset = queryset.filter(season__year__gte=CONSTRUCTORS_TITLES_FROM)
    rows = (
        queryset.order_by("season__year", "after_round", f"{field}_id")
        .values_list("season__year", "after_round", f"{field}_id")
        .distinct()
    )
    result: dict[int, int] = {}
    for year, after_round, entity_id in rows:
        if after_round == last_round.get(year):
            result.setdefault(year, entity_id)
    return result


def title_counts(kind: Kind, champion_map: dict[int, int] | None = None) -> dict[int, int]:
    """Entity id -> number of championships (entities without a title are absent)."""
    counts: dict[int, int] = {}
    for entity_id in (champion_map if champion_map is not None else champions(kind)).values():
        counts[entity_id] = counts.get(entity_id, 0) + 1
    return counts


def entity_summary(kind: Kind, entity_id: int) -> dict:
    """Titles and season positions of one driver or constructor in a single query.

    Returns {"titles": int, "positions": {year: position}}. `positions` uses the newest table of
    each season (final once the season is over, current while it runs; absent when the entity is
    not in that table). A title is position 1 after the last round of a finished season, with
    the same rules as `champions`.
    """
    model = _model(kind)
    season_model = _season_model()
    newest = (
        model.objects.filter(season_id=OuterRef("season_id"))
        .order_by()
        .values("season_id")
        .annotate(last=Max("after_round"))
        .values("last")
    )
    last_round = (
        season_model.objects.filter(pk=OuterRef("season_id"))
        .order_by()
        .values("pk")
        .annotate(last=Max("rounds__round", filter=Q(rounds__is_cancelled=False)))
        .values("last")
    )
    race_has_results = Exists(
        season_model.objects.filter(
            pk=OuterRef("season_id"),
            rounds__round=OuterRef("after_round"),
            rounds__sessions__type="RACE",
            rounds__sessions__results__isnull=False,
        )
    )
    rows = (
        model.objects.filter(**{f"{_ENTITY_FIELD[kind]}_id": entity_id})
        .annotate(
            newest=Subquery(newest),
            last_round=Subquery(last_round),
            race_has_results=race_has_results,
        )
        .values_list(
            "season__year", "after_round", "position", "newest", "last_round", "race_has_results"
        )
    )
    min_year = CONSTRUCTORS_TITLES_FROM if kind == "constructors" else 0
    titles = 0
    positions: dict[int, int | None] = {}
    for year, after_round, position, newest_round, last, has_results in rows:
        if after_round == newest_round:
            positions[year] = position
        if position == 1 and after_round == last and has_results and year >= min_year:
            titles += 1
    return {"titles": titles, "positions": positions}


def season_positions(kind: Kind, season_id: int) -> dict[int, int | None]:
    """Entity id -> position in the newest table of one season (one query, empty if none)."""
    after_round = latest_round(kind, season_id)
    if after_round is None:
        return {}
    field = _ENTITY_FIELD[kind]
    return dict(
        _model(kind)
        .objects.filter(season_id=season_id, after_round=after_round)
        .values_list(f"{field}_id", "position")
    )


# --- Title race (FR-305) ---------------------------------------------------------------------


@dataclass(frozen=True)
class Scoring:
    """What a driver can score at most in one race and in one sprint."""

    race_win: int
    fastest_lap_point: bool
    sprint_win: int

    @property
    def race_max(self) -> int:
        return self.race_win + (1 if self.fastest_lap_point else 0)


def default_scoring(year: int) -> Scoring:
    """Maximum points per round by era, used when the season has no PointsSystem rows.

    Race winner: 8 (1950-59), 9 (1960-90), 10 (1991-2009), 25 (2010 on; 25-18-15-12-10-8-6-4-2-1).
    Fastest-lap point (only for a top-10 finisher): 1950-59 and 2019-2024; not before or after.
    Sprint winner: 3 in 2021, 8 from 2022 (8-7-6-5-4-3-2-1); no sprints before 2021.
    Known limits: dropped results (before 1991) and the double points of the 2014 finale are
    not modelled; the endpoint is meant for ongoing seasons.
    """
    if year >= 2010:
        race_win = 25
    elif year >= 1991:
        race_win = 10
    elif year >= 1960:
        race_win = 9
    else:
        race_win = 8
    fastest_lap = year <= 1959 or 2019 <= year <= 2024
    sprint_win = 8 if year >= 2022 else 3 if year == 2021 else 0
    return Scoring(race_win, fastest_lap, sprint_win)


def title_chances(
    points: dict[int, Decimal],
    remaining_races: int,
    remaining_sprints: int,
    scoring: Scoring,
) -> dict:
    """Pure arithmetic of the championship fight. `points` maps driver id -> current points.

    Every driver can gain at most `remaining_races * scoring.race_max + remaining_sprints *
    scoring.sprint_win` points, so max_points = points + that. A driver can still be champion
    when max_points >= the best current total among the others (the others scoring nothing is
    the best case). Equality is only a tie on points, which the countback (wins, then second
    places...) settles; such a driver is flagged `tie_break_needed`, not excluded. The title is
    decided when one driver has strictly more points than every other driver's max_points.

    Returns {"max_available": gain, "drivers": {id: {max_points, can_win, tie_break_needed}},
    "champion": id or None}.
    """
    gain = Decimal(remaining_races * scoring.race_max + remaining_sprints * scoring.sprint_win)
    maxima = {driver_id: total + gain for driver_id, total in points.items()}
    drivers = {}
    champion = None
    for driver_id, total in points.items():
        others = [t for o, t in points.items() if o != driver_id]
        best_other = max(others, default=Decimal(-1))
        drivers[driver_id] = {
            "max_points": maxima[driver_id],
            "can_win": maxima[driver_id] >= best_other,
            "tie_break_needed": maxima[driver_id] == best_other,
        }
        other_maxima = [m for o, m in maxima.items() if o != driver_id]
        if total > max(other_maxima, default=Decimal(-1)):
            champion = driver_id
    return {"max_available": gain, "drivers": drivers, "champion": champion}


def _round_plan(season_id: int) -> tuple[dict[int, bool], Scoring, int]:
    """(round number -> has sprint for non-cancelled rounds, scoring from PointsSystem, year)."""
    season_model = _season_model()
    rounds: dict[int, bool] = {}
    rows = season_model.objects.filter(
        pk=season_id, rounds__is_cancelled=False, rounds__round__isnull=False
    ).values_list("rounds__round", "rounds__sessions__type")
    for number, session_type in rows:
        rounds[number] = rounds.get(number, False) or session_type == "SPRINT"
    systems = {
        kind: (positions, fl)
        for kind, positions, fl in season_model.objects.filter(
            pk=season_id, points_systems__isnull=False
        ).values_list(
            "points_systems__session_type",
            "points_systems__points_by_position",
            "points_systems__fastest_lap_point",
        )
    }
    year = season_model.objects.values_list("year", flat=True).get(pk=season_id)
    scoring = default_scoring(year)
    if "race" in systems and systems["race"][0]:
        scoring = Scoring(
            race_win=systems["race"][0][0],
            fastest_lap_point=bool(systems["race"][1]),
            sprint_win=(
                systems["sprint"][0][0] if systems.get("sprint") and systems["sprint"][0] else 0
            ),
        )
    return rounds, scoring, year


def title_race(season_id: int) -> dict | None:
    """Title fight of one season from the newest driver table; None without standings.

    Returns {"year", "after_round", "rounds_remaining", "sprints_remaining", "max_available",
    "fastest_lap_point", "champion" (driver entity or None), "decided_in_round" (or None),
    "contenders": [row + max_points, tie_break_needed], "eliminated": count}.
    Queries: round plan (3), tables (2).
    """
    rows_all = list(
        DriverStanding.objects.filter(season_id=season_id).values_list(
            "after_round", "driver_id", "points"
        )
    )
    if not rows_all:
        return None
    rounds, scoring, year = _round_plan(season_id)
    by_round: dict[int, dict[int, Decimal]] = {}
    for after_round, driver_id, points in rows_all:
        by_round.setdefault(after_round, {})[driver_id] = points

    def remaining(after_round: int) -> tuple[int, int]:
        later = [number for number in rounds if number > after_round]
        return len(later), sum(1 for number in later if rounds[number])

    decided_in = None
    for after_round in sorted(by_round):
        races, sprints = remaining(after_round)
        decided = title_chances(by_round[after_round], races, sprints, scoring)["champion"]
        if decided is None:
            decided_in = None
        elif decided_in is None:
            decided_in = after_round

    last = max(by_round)
    races, sprints = remaining(last)
    chances = title_chances(by_round[last], races, sprints, scoring)
    table = standings_rows("drivers", season_id, last)
    champion_id = chances["champion"]
    if champion_id is None and races == 0 and sprints == 0:
        # Season over with equal points: the official classification settles it.
        official = [r for r in table if r["position"] == 1]
        if len(official) == 1:
            champion_id = official[0]["entity"]["id"]
            decided_in = last
    contenders = []
    for row in table:
        info = chances["drivers"][row["entity"]["id"]]
        if champion_id is not None:
            if row["entity"]["id"] != champion_id:
                continue
        elif not info["can_win"]:
            continue
        contenders.append(
            {**row, "max_points": info["max_points"], "tie_break_needed": info["tie_break_needed"]}
        )
    champion = next((r["entity"] for r in contenders if r["entity"]["id"] == champion_id), None)
    return {
        "year": year,
        "after_round": last,
        "rounds_remaining": races,
        "sprints_remaining": sprints,
        "max_available": chances["max_available"],
        "fastest_lap_point": scoring.fastest_lap_point,
        "champion": champion,
        "decided_in_round": decided_in if champion_id is not None else None,
        "contenders": contenders,
        "eliminated": len(table) - len(contenders),
    }

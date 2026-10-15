"""Read side: lookups over imported standings. Catalog data is reached via FK joins only."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

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

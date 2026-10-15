"""Write side: idempotent replacement of one imported standings table."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction

from .models import ConstructorStanding, DriverStanding


@dataclass(frozen=True)
class DriverStandingRow:
    driver_id: int
    position: int | None
    position_text: str
    points: Decimal | str | int | float
    wins: int = 0
    podiums: int = 0


@dataclass(frozen=True)
class ConstructorStandingRow:
    constructor_id: int
    position: int | None
    position_text: str
    points: Decimal | str | int | float
    wins: int = 0
    podiums: int = 0


def _get(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(name, default)
    return getattr(row, name, default)


def _replace(model, key: str, season_id: int, after_round: int, rows: Iterable[Any]) -> dict:
    if after_round < 1:
        raise ValueError("after_round must be >= 1")
    prepared: dict[int, dict] = {}
    for row in rows:
        key_id = _get(row, key)
        if key_id is None:
            raise ValueError(f"row is missing {key}")
        if key_id in prepared:
            raise ValueError(f"duplicate {key} {key_id} in rows")
        prepared[key_id] = {
            "position": _get(row, "position"),
            "position_text": _get(row, "position_text", "") or "",
            "points": Decimal(str(_get(row, "points", 0))),
            "wins": _get(row, "wins", 0) or 0,
            "podiums": _get(row, "podiums", 0) or 0,
        }

    scope = model.objects.filter(season_id=season_id, after_round=after_round)
    with transaction.atomic():
        existing = {getattr(obj, key): obj for obj in scope.select_for_update()}
        stale = [obj.pk for k, obj in existing.items() if k not in prepared]
        deleted = len(stale)
        if stale:
            model.objects.filter(pk__in=stale).delete()

        to_create, to_update = [], []
        update_fields = ["position", "position_text", "points", "wins", "podiums"]
        for key_id, values in prepared.items():
            obj = existing.get(key_id)
            if obj is None:
                to_create.append(
                    model(season_id=season_id, after_round=after_round, **{key: key_id}, **values)
                )
            elif any(getattr(obj, field) != value for field, value in values.items()):
                for field, value in values.items():
                    setattr(obj, field, value)
                to_update.append(obj)
        model.objects.bulk_create(to_create)
        if to_update:
            model.objects.bulk_update(to_update, update_fields)
    return {"created": len(to_create), "updated": len(to_update), "deleted": deleted}


def replace_driver_standings(season_id: int, after_round: int, rows: Iterable[Any]) -> dict:
    """Make the driver table after `after_round` equal to `rows`.

    Rows are mappings or objects with driver_id, position, position_text, points, wins,
    podiums. Returns {"created", "updated", "deleted"}. Safe to call repeatedly.
    """
    return _replace(DriverStanding, "driver_id", season_id, after_round, rows)


def replace_constructor_standings(season_id: int, after_round: int, rows: Iterable[Any]) -> dict:
    """Same as replace_driver_standings, for the constructors' table."""
    return _replace(ConstructorStanding, "constructor_id", season_id, after_round, rows)

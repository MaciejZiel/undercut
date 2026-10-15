"""Account data export (GDPR): the user's predictions and leagues."""

from __future__ import annotations

from apps.catalog import selectors as catalog

from .models import LeagueMembership, Prediction

PROVIDER_NAME = "predictions"


def export_user_data(user) -> dict:
    predictions = list(Prediction.objects.filter(user=user).order_by("round_id"))
    rounds = catalog.round_refs([p.round_id for p in predictions])
    return {
        "predictions": [
            {
                "season": rounds.get(p.round_id, {}).get("year"),
                "round": rounds.get(p.round_id, {}).get("round"),
                "p1_driver_id": p.p1_id,
                "p2_driver_id": p.p2_id,
                "p3_driver_id": p.p3_id,
                "pole_driver_id": p.pole_id,
                "fastest_lap_driver_id": p.fastest_lap_id,
                "points": p.points,
                "breakdown": p.breakdown,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in predictions
        ],
        "leagues": [
            {
                "name": m.league.name,
                "is_owner": m.league.owner_id == user.pk,
                "joined_at": m.joined_at.isoformat(),
            }
            for m in LeagueMembership.objects.filter(user=user).select_related("league")
        ],
    }


def register() -> None:
    try:
        from apps.accounts.exports import register_export_provider
    except ImportError:
        # TODO: apps.accounts.exports is being written by another change; once it exists this
        # registers automatically. Assumed contract: register_export_provider(name, func(user)).
        return
    register_export_provider(PROVIDER_NAME, export_user_data)

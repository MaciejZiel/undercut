"""Read-only functions of predictions that other modules may call (no model imports needed)."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.catalog import selectors as catalog

from .models import Prediction

SLOTS = ("p1", "p2", "p3", "pole", "fastest_lap")
# Order and labels of the points breakdown shown to the user.
BREAKDOWN_LABELS = (
    ("p1", "P1"),
    ("p2", "P2"),
    ("p3", "P3"),
    ("pole", "Pole position"),
    ("fastest_lap", "Fastest lap"),
    ("exact_podium_bonus", "Exact podium bonus"),
)


@dataclass(frozen=True)
class UserRoundResult:
    """A user's pick for a round with the points it earned (points None while unscored)."""

    user_id: int
    round_id: int
    picks: dict[str, str]  # slot -> driver name
    points: int | None
    breakdown: dict = field(default_factory=dict)

    @property
    def breakdown_rows(self) -> list[tuple[str, int]]:
        """(label, points) for every component the scoring could judge."""
        return [
            (label, self.breakdown[key])
            for key, label in BREAKDOWN_LABELS
            if self.breakdown.get(key) is not None
        ]


def user_round_result(user_id: int, round_id: int) -> UserRoundResult | None:
    """The user's prediction for a round, or None when they did not predict. Two queries."""
    prediction = Prediction.objects.filter(user_id=user_id, round_id=round_id).first()
    if prediction is None:
        return None
    labels = catalog.driver_labels([getattr(prediction, f"{slot}_id") for slot in SLOTS])
    picks = {
        slot: labels.get(getattr(prediction, f"{slot}_id"), {}).get("name", "?") for slot in SLOTS
    }
    return UserRoundResult(
        user_id=user_id,
        round_id=round_id,
        picks=picks,
        points=prediction.points,
        breakdown=prediction.breakdown or {},
    )


def has_prediction(user_id: int, round_id: int) -> bool:
    return Prediction.objects.filter(user_id=user_id, round_id=round_id).exists()

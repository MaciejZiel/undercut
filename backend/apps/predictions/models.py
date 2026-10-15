import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from . import config


def generate_invite_code() -> str:
    return "".join(
        secrets.choice(config.INVITE_CODE_ALPHABET) for _ in range(config.INVITE_CODE_LENGTH)
    )


class Prediction(models.Model):
    # SET_NULL keeps the pick (and its points) when the account is deleted; shown as
    # "Deleted user".
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="predictions",
    )
    round = models.ForeignKey("catalog.Round", on_delete=models.CASCADE, related_name="predictions")
    p1 = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")
    p2 = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")
    p3 = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")
    pole = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")
    fastest_lap = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")
    # Null until the race is scored (or when the result holds no data).
    points = models.PositiveSmallIntegerField(null=True, blank=True)
    # Per-component points plus exact_hits (int), exact_podium (bool) and pole_hit (bool).
    breakdown = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["round_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "round"],
                condition=Q(user__isnull=False),
                name="predictions_prediction_user_round_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(p1=F("p2")) & ~Q(p1=F("p3")) & ~Q(p2=F("p3")),
                name="predictions_prediction_podium_distinct",
            ),
        ]
        indexes = [models.Index(fields=["round", "points"], name="predictions_round_points_idx")]

    def __str__(self):
        return f"Prediction {self.pk} (round {self.round_id})"


class League(models.Model):
    name = models.CharField(max_length=60)
    # SET_NULL: a deleted owner leaves the league running without an owner.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_leagues",
    )
    invite_code = models.CharField(max_length=config.INVITE_CODE_LENGTH, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(invite_code__regex=rf"^.{{{config.INVITE_CODE_LENGTH}}}$"),
                name="predictions_league_code_length",
            )
        ]

    def __str__(self):
        return self.name


class LeagueMembership(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="league_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["league", "user"], name="predictions_membership_league_user_uniq"
            )
        ]

    def __str__(self):
        return f"{self.user_id} in {self.league_id}"

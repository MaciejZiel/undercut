from django.db import models
from django.db.models import Q


class _StandingBase(models.Model):
    """Imported (never computed) championship table after a given round."""

    season = models.ForeignKey("catalog.Season", on_delete=models.CASCADE, related_name="+")
    after_round = models.PositiveSmallIntegerField()
    # Some entries have no classified position (e.g. disqualified from the championship).
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    position_text = models.CharField(max_length=4, blank=True)
    # Half points exist (shortened races, shared drives), hence two decimals.
    points = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    podiums = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True


class DriverStanding(_StandingBase):
    driver = models.ForeignKey("catalog.Driver", on_delete=models.CASCADE, related_name="standings")

    class Meta:
        ordering = ["season_id", "after_round", "position", "-points", "driver_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "after_round", "driver"],
                name="standings_driverstanding_uniq",
            ),
            models.CheckConstraint(
                condition=Q(points__gte=0), name="standings_driverstanding_points_nonneg"
            ),
            models.CheckConstraint(
                condition=Q(position__isnull=True) | Q(position__gte=1),
                name="standings_driverstanding_position_pos",
            ),
        ]
        indexes = [
            models.Index(
                fields=["season", "after_round", "position"], name="standings_ds_lookup_idx"
            ),
        ]

    def __str__(self):
        return f"{self.season_id} R{self.after_round} P{self.position_text or '-'} {self.driver_id}"


class ConstructorStanding(_StandingBase):
    constructor = models.ForeignKey(
        "catalog.Constructor", on_delete=models.CASCADE, related_name="standings"
    )

    class Meta:
        ordering = ["season_id", "after_round", "position", "-points", "constructor_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "after_round", "constructor"],
                name="standings_constructorstanding_uniq",
            ),
            models.CheckConstraint(
                condition=Q(points__gte=0), name="standings_constructorstanding_points_nonneg"
            ),
            models.CheckConstraint(
                condition=Q(position__isnull=True) | Q(position__gte=1),
                name="standings_constructorstanding_position_pos",
            ),
        ]
        indexes = [
            models.Index(
                fields=["season", "after_round", "position"], name="standings_cs_lookup_idx"
            ),
        ]

    def __str__(self):
        return (
            f"{self.season_id} R{self.after_round} P{self.position_text or '-'} "
            f"{self.constructor_id}"
        )

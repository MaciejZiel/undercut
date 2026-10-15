"""Race analytics from OpenF1 (seasons 2023 onwards).

Rows belong to a catalog Session and Driver (string foreign keys, so this module never imports
catalog models). Durations are stored in milliseconds; OpenF1 returns seconds as floats.
"""

from django.db import models
from django.db.models import Q


class SessionDriverRow(models.Model):
    """Shared shape: one row of a session belonging to one driver."""

    session = models.ForeignKey("catalog.Session", on_delete=models.CASCADE, related_name="+")
    driver = models.ForeignKey("catalog.Driver", on_delete=models.PROTECT, related_name="+")

    class Meta:
        abstract = True


class Lap(SessionDriverRow):
    lap_number = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    sector1_ms = models.PositiveIntegerField(null=True, blank=True)
    sector2_ms = models.PositiveIntegerField(null=True, blank=True)
    sector3_ms = models.PositiveIntegerField(null=True, blank=True)
    is_pit_out_lap = models.BooleanField(default=False)
    date_start = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "driver_id", "lap_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver", "lap_number"], name="analytics_lap_uniq"
            ),
            models.CheckConstraint(condition=Q(lap_number__gte=1), name="analytics_lap_number_pos"),
        ]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class Stint(SessionDriverRow):
    class Compound(models.TextChoices):
        SOFT = "SOFT", "Soft"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        WET = "WET", "Wet"
        UNKNOWN = "UNKNOWN", "Unknown"

    stint_number = models.PositiveSmallIntegerField()
    compound = models.CharField(max_length=12, choices=Compound.choices, default=Compound.UNKNOWN)
    lap_start = models.PositiveSmallIntegerField(null=True, blank=True)
    lap_end = models.PositiveSmallIntegerField(null=True, blank=True)
    tyre_age_at_start = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "driver_id", "stint_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver", "stint_number"], name="analytics_stint_uniq"
            ),
            models.CheckConstraint(
                condition=Q(lap_start__isnull=True)
                | Q(lap_end__isnull=True)
                | Q(lap_end__gte=models.F("lap_start")),
                name="analytics_stint_laps_ordered",
            ),
        ]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class PitStop(SessionDriverRow):
    date = models.DateTimeField()
    lap_number = models.PositiveSmallIntegerField(null=True, blank=True)
    # stop_ms (stationary time) is only published from the 2024 US GP onwards.
    stop_ms = models.PositiveIntegerField(null=True, blank=True)
    lane_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "date"]
        constraints = [
            models.UniqueConstraint(fields=["session", "driver", "date"], name="analytics_pit_uniq")
        ]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class PositionSample(SessionDriverRow):
    ts = models.DateTimeField()
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["session_id", "ts"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver", "ts"], name="analytics_position_uniq"
            ),
            models.CheckConstraint(condition=Q(position__gte=1), name="analytics_position_pos"),
        ]
        indexes = [models.Index(fields=["session", "ts"], name="analytics_position_ts_idx")]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class IntervalSample(SessionDriverRow):
    """Gap to the leader and to the car ahead. OpenF1 sends a float, "+1 LAP" text or null."""

    ts = models.DateTimeField()
    gap_to_leader_ms = models.IntegerField(null=True, blank=True)
    gap_to_leader_text = models.CharField(max_length=16, blank=True)
    interval_ms = models.IntegerField(null=True, blank=True)
    interval_text = models.CharField(max_length=16, blank=True)

    class Meta:
        ordering = ["session_id", "ts"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver", "ts"], name="analytics_interval_uniq"
            )
        ]
        indexes = [models.Index(fields=["session", "ts"], name="analytics_interval_ts_idx")]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class RaceControlMessage(models.Model):
    session = models.ForeignKey("catalog.Session", on_delete=models.CASCADE, related_name="+")
    driver = models.ForeignKey(
        "catalog.Driver", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    ts = models.DateTimeField()
    lap_number = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.CharField(max_length=40, blank=True)
    flag = models.CharField(max_length=40, blank=True)
    scope = models.CharField(max_length=40, blank=True)
    sector = models.PositiveSmallIntegerField(null=True, blank=True)
    qualifying_phase = models.PositiveSmallIntegerField(null=True, blank=True)
    message = models.TextField()

    class Meta:
        ordering = ["session_id", "ts", "id"]
        constraints = [
            # OpenF1 has no message id; the natural key is time + text + driver.
            models.UniqueConstraint(
                fields=["session", "ts", "message"],
                condition=Q(driver__isnull=True),
                name="analytics_rcm_uniq_no_driver",
            ),
            models.UniqueConstraint(
                fields=["session", "ts", "message", "driver"],
                condition=Q(driver__isnull=False),
                name="analytics_rcm_uniq_driver",
            ),
        ]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"


class WeatherSample(models.Model):
    session = models.ForeignKey("catalog.Session", on_delete=models.CASCADE, related_name="+")
    ts = models.DateTimeField()
    air_temperature = models.FloatField(null=True, blank=True)
    track_temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)
    wind_speed = models.FloatField(null=True, blank=True)
    wind_direction = models.PositiveSmallIntegerField(null=True, blank=True)
    rainfall = models.BooleanField(default=False)

    class Meta:
        ordering = ["session_id", "ts"]
        constraints = [
            models.UniqueConstraint(fields=["session", "ts"], name="analytics_weather_uniq")
        ]

    def __str__(self) -> str:
        return f"{type(self).__name__}#{self.pk}"

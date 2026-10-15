from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from .text import make_search_name

COLOR_HEX_VALIDATOR = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use the #rrggbb format.")


class Season(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return self.name or str(self.year)


class PointsSystem(models.Model):
    class SessionType(models.TextChoices):
        RACE = "race", "Race"
        SPRINT = "sprint", "Sprint"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="points_systems")
    session_type = models.CharField(max_length=10, choices=SessionType.choices)
    points_by_position = models.JSONField(default=list, help_text="Points for P1, P2, ...")
    fastest_lap_point = models.BooleanField(default=False)
    fastest_lap_min_position = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-season__year", "session_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "session_type"], name="catalog_pointssystem_season_type_uniq"
            ),
            models.CheckConstraint(
                condition=Q(session_type__in=["race", "sprint"]),
                name="catalog_pointssystem_type_valid",
            ),
        ]

    def __str__(self):
        return f"{self.season} {self.session_type}"


class Circuit(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    jolpica_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200)
    locality = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    timezone = models.CharField(
        max_length=64, blank=True, help_text="IANA name, e.g. Europe/Warsaw"
    )
    length_m = models.PositiveIntegerField(null=True, blank=True)
    lap_record_ms = models.PositiveIntegerField(null=True, blank=True)
    lap_record_driver = models.CharField(max_length=200, blank=True)
    lap_record_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["jolpica_id"],
                condition=~Q(jolpica_id=""),
                name="catalog_circuit_jolpica_id_uniq",
            ),
        ]

    def __str__(self):
        return self.name


class Constructor(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    jolpica_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200)
    nationality = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["jolpica_id"],
                condition=~Q(jolpica_id=""),
                name="catalog_constructor_jolpica_id_uniq",
            ),
        ]

    def __str__(self):
        return self.name


class ConstructorSeason(models.Model):
    constructor = models.ForeignKey(Constructor, on_delete=models.CASCADE, related_name="seasons")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="constructor_seasons")
    display_name = models.CharField(max_length=200, blank=True)
    # null means "neutral colour" (no data), so NULL is intentional here.
    color_hex = models.CharField(  # noqa: DJ001
        max_length=7, null=True, blank=True, validators=[COLOR_HEX_VALIDATOR]
    )

    class Meta:
        ordering = ["-season__year", "constructor__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["constructor", "season"], name="catalog_constructorseason_uniq"
            ),
        ]

    def __str__(self):
        return f"{self.display_name or self.constructor} {self.season.year}"


class Driver(models.Model):
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    jolpica_id = models.CharField(max_length=100, blank=True)
    given_name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100)
    code = models.CharField(max_length=3, blank=True)
    permanent_number = models.PositiveSmallIntegerField(null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    headshot_url = models.URLField(max_length=500, blank=True)
    search_name = models.CharField(max_length=250, blank=True, editable=False, db_index=True)

    class Meta:
        ordering = ["family_name", "given_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["jolpica_id"],
                condition=~Q(jolpica_id=""),
                name="catalog_driver_jolpica_id_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def save(self, *args, **kwargs):
        self.search_name = make_search_name(self.given_name, self.family_name)
        if not self.slug:
            self.slug = slugify(self.search_name)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "search_name", "slug"}
        super().save(*args, **kwargs)


class Round(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="rounds")
    round = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200)
    circuit = models.ForeignKey(Circuit, on_delete=models.PROTECT, related_name="rounds")
    date = models.DateField()
    scheduled_laps = models.PositiveSmallIntegerField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)
    openf1_meeting_key = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ["season__year", "round"]
        constraints = [
            models.UniqueConstraint(fields=["season", "round"], name="catalog_round_season_uniq"),
            models.CheckConstraint(condition=Q(round__gte=1), name="catalog_round_number_pos"),
        ]

    def __str__(self):
        return f"{self.season.year} R{self.round} {self.name}"


class Session(models.Model):
    class Type(models.TextChoices):
        FP1 = "FP1", "Practice 1"
        FP2 = "FP2", "Practice 2"
        FP3 = "FP3", "Practice 3"
        SQ = "SQ", "Sprint qualifying"
        SPRINT = "SPRINT", "Sprint"
        Q = "Q", "Qualifying"
        RACE = "RACE", "Race"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        FINISHED = "finished", "Finished"
        RESULTS_FINAL = "results_final", "Results final"

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="sessions")
    type = models.CharField(max_length=6, choices=Type.choices)
    start_utc = models.DateTimeField(null=True, blank=True)
    end_utc = models.DateTimeField(null=True, blank=True)
    openf1_session_key = models.PositiveIntegerField(null=True, blank=True, unique=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ["round__season__year", "round__round", "start_utc", "type"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "type"], name="catalog_session_round_type_uniq"
            ),
            models.CheckConstraint(
                condition=Q(type__in=["FP1", "FP2", "FP3", "SQ", "SPRINT", "Q", "RACE"]),
                name="catalog_session_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["scheduled", "live", "finished", "results_final"]),
                name="catalog_session_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(start_utc__isnull=True)
                | Q(end_utc__isnull=True)
                | Q(end_utc__gt=models.F("start_utc")),
                name="catalog_session_end_after_start",
            ),
        ]
        indexes = [models.Index(fields=["status", "start_utc"], name="catalog_session_status_idx")]

    def __str__(self):
        return f"{self.round} {self.type}"


class Result(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="results")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="results")
    # The team on race day; never derived from the driver's current team.
    constructor = models.ForeignKey(Constructor, on_delete=models.PROTECT, related_name="results")
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    position_text = models.CharField(max_length=4, blank=True)
    grid = models.PositiveSmallIntegerField(null=True, blank=True)
    laps = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=100, blank=True)
    time_ms = models.BigIntegerField(null=True, blank=True)
    best_lap_ms = models.PositiveIntegerField(null=True, blank=True)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fastest_lap_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    manual_override = models.BooleanField(default=False)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "position", "driver_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver"], name="catalog_result_session_driver_uniq"
            ),
            models.UniqueConstraint(
                fields=["session", "position"],
                condition=Q(position__isnull=False),
                name="catalog_result_session_position_uniq",
            ),
            models.UniqueConstraint(
                fields=["session"],
                condition=Q(fastest_lap_rank=1),
                name="catalog_result_one_fastest_lap",
            ),
            models.CheckConstraint(
                condition=Q(position__isnull=True) | Q(position__gte=1),
                name="catalog_result_position_pos",
            ),
            models.CheckConstraint(
                condition=Q(fastest_lap_rank__isnull=True) | Q(fastest_lap_rank__gte=1),
                name="catalog_result_fl_rank_pos",
            ),
            models.CheckConstraint(condition=Q(points__gte=0), name="catalog_result_points_nonneg"),
        ]
        indexes = [
            models.Index(fields=["driver", "session"], name="catalog_result_driver_idx"),
            models.Index(fields=["constructor", "session"], name="catalog_result_ctor_idx"),
        ]

    def __str__(self):
        return f"{self.session} {self.position_text or self.position or '-'} {self.driver}"


class QualifyingResult(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="qualifying_results"
    )
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="qualifying_results")
    constructor = models.ForeignKey(
        Constructor, on_delete=models.PROTECT, related_name="qualifying_results"
    )
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    q1_ms = models.PositiveIntegerField(null=True, blank=True)
    q2_ms = models.PositiveIntegerField(null=True, blank=True)
    q3_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "position", "driver_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "driver"], name="catalog_qualifying_session_driver_uniq"
            ),
            models.UniqueConstraint(
                fields=["session", "position"],
                condition=Q(position__isnull=False),
                name="catalog_qualifying_session_position_uniq",
            ),
            models.CheckConstraint(
                condition=Q(position__isnull=True) | Q(position__gte=1),
                name="catalog_qualifying_position_pos",
            ),
        ]

    def __str__(self):
        return f"{self.session} Q {self.position or '-'} {self.driver}"

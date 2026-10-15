from django.db import models


class SyncRun(models.Model):
    """One execution of an import or sync job, with its counters."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    source = models.CharField(max_length=50, help_text="e.g. jolpica-dump, jolpica-api, openf1")
    job = models.CharField(max_length=100, help_text="e.g. import_history")
    scope = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.RUNNING)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [models.Index(fields=["source", "job", "-started_at"], name="syncrun_job_idx")]

    def __str__(self) -> str:
        return f"{self.source}/{self.job} #{self.pk} [{self.status}]"


class DriverNumberMap(models.Model):
    """OpenF1 identifies drivers by car number, which differs between seasons.

    Built automatically by the OpenF1 importer (name_acronym == Driver.code, then surname);
    a row that already exists is never overwritten, so a human fix in the admin sticks.
    """

    season_year = models.PositiveSmallIntegerField()
    driver_number = models.PositiveSmallIntegerField()
    driver = models.ForeignKey("catalog.Driver", on_delete=models.CASCADE, related_name="+")

    class Meta:
        ordering = ["-season_year", "driver_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["season_year", "driver_number"], name="ingestion_drivernumber_uniq"
            )
        ]

    def __str__(self) -> str:
        return f"{self.season_year} #{self.driver_number} -> driver {self.driver_id}"

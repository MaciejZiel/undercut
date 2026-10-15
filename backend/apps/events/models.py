from django.db import models


class OutboxEvent(models.Model):
    """A domain event written in the same transaction as the data change that caused it."""

    class Status(models.TextChoices):
        PENDING = "pending"
        DONE = "done"
        DEAD = "dead"

    type = models.CharField(max_length=100)
    # Ordering/grouping key, e.g. "session:42". Events with one key are handled in id order.
    key = models.CharField(max_length=100, blank=True)
    # Thin payload: identifiers and a version, never a copy of the data.
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(db_default=models.functions.Now())
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "available_at", "id"], name="outbox_due_idx")]
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.type}#{self.pk} [{self.status}]"


class ScheduleSlot(models.Model):
    """One fired occurrence of a recurring job. The unique pair makes publishing idempotent."""

    job = models.CharField(max_length=100)
    slot = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "slot"], name="uniq_job_slot")]

    def __str__(self) -> str:
        return f"{self.job} @ {self.slot:%Y-%m-%d %H:%M}"

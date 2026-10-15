from django.db import models


class Heartbeat(models.Model):
    """Last sign of life of a long-running process (scheduler, outbox worker).

    One row per process name, updated in place, so the table never grows.
    """

    name = models.CharField(max_length=50, unique=True)
    beat_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.name} @ {self.beat_at:%Y-%m-%d %H:%M:%S}"

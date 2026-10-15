from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user, added before the first migration (AUTH_USER_MODEL is hard to swap later)."""

    display_name = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, default="UTC")
    theme = models.CharField(
        max_length=10,
        choices=[("system", "System"), ("light", "Light"), ("dark", "Dark")],
        default="system",
    )
    is_demo = models.BooleanField(default=False)

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


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

    class Meta(AbstractUser.Meta):
        constraints = [
            # Display names are unique regardless of case ("Max" and "max" are the same person).
            models.UniqueConstraint(Lower("display_name"), name="accounts_user_display_name_ci"),
        ]

    @property
    def can_predict(self) -> bool:
        """An unverified account can browse but not act (FR-501)."""
        return self.is_active and self.email_verified


class Favorite(models.Model):
    """A favourite driver or constructor. Exactly one of the two targets is set."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    # String references: modules never import each other's models.
    driver = models.ForeignKey(
        "catalog.Driver", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    constructor = models.ForeignKey(
        "catalog.Constructor", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(driver__isnull=False, constructor__isnull=True)
                    | Q(driver__isnull=True, constructor__isnull=False)
                ),
                name="accounts_favorite_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "driver"],
                condition=Q(driver__isnull=False),
                name="accounts_favorite_user_driver_uniq",
            ),
            models.UniqueConstraint(
                fields=["user", "constructor"],
                condition=Q(constructor__isnull=False),
                name="accounts_favorite_user_constructor_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.driver_id or self.constructor_id}"


class GoogleIdentity(models.Model):
    """A Google account linked to a user. ``sub`` is Google's stable id; the e-mail may change."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="google_identity"
    )
    sub = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user_id} <-> google:{self.sub}"

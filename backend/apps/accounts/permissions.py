"""Permission classes other modules can use on their endpoints."""

from rest_framework.permissions import BasePermission


class CanPredict(BasePermission):
    """Authenticated, active and e-mail verified (FR-501: unverified accounts only browse)."""

    message = "Confirm your e-mail address to do this."
    code = "email_not_verified"

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.can_predict)

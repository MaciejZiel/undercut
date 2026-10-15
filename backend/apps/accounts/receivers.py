from . import services


def sync_email_verified(sender=None, request=None, user=None, email_address=None, **kwargs) -> None:
    """allauth signal receiver (email_confirmed passes only ``email_address``)."""
    user = user or getattr(email_address, "user", None)
    if user is not None:
        services.sync_email_verified(user)

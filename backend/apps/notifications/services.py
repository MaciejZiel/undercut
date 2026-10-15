from .models import NotificationPref


def get_pref(user) -> NotificationPref:
    pref, _ = NotificationPref.objects.get_or_create(user=user)
    return pref


def race_result_email_enabled(user) -> bool:
    pref = NotificationPref.objects.filter(user=user).first()
    return bool(pref and pref.race_result_email)


def set_race_result_email(user, enabled: bool) -> NotificationPref:
    pref = get_pref(user)
    if pref.race_result_email != enabled:
        pref.race_result_email = enabled
        pref.save(update_fields=["race_result_email", "updated_at"])
    return pref


def unsubscribe(token: str) -> NotificationPref | None:
    """Switch race-result e-mails off for the owner of ``token``. Idempotent; None if unknown."""
    pref = NotificationPref.objects.filter(unsubscribe_token=token).first()
    if pref is None:
        return None
    if pref.race_result_email:
        pref.race_result_email = False
        pref.save(update_fields=["race_result_email", "updated_at"])
    return pref


def export_user_data(user) -> dict:
    """Export provider: the user's notification preferences."""
    pref = NotificationPref.objects.filter(user=user).first()
    return {"race_result_email": bool(pref and pref.race_result_email)}

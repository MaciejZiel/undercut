import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_returns_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_custom_user_model_is_active():
    from django.contrib.auth import get_user_model

    assert get_user_model()._meta.label == "accounts.User"

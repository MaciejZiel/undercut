import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.catalog.models import Circuit, Round, Season, Session

pytestmark = pytest.mark.django_db


def seed(*args) -> dict:
    out = StringIO()
    call_command("seed_e2e", *args, stdout=out)
    return json.loads(out.getvalue().strip().splitlines()[-1])


def make_round(year: int, number: int, *, cancelled=False) -> Round:
    season, _ = Season.objects.get_or_create(year=year)
    circuit, _ = Circuit.objects.get_or_create(slug=f"circuit-{year}-{number}", name=f"C{number}")
    return Round.objects.create(
        season=season,
        round=number,
        name=f"Grand Prix {year}-{number}",
        circuit=circuit,
        date=f"{year}-03-01",
        is_cancelled=cancelled,
    )


def test_fails_without_data():
    with pytest.raises(CommandError):
        seed()


def test_opens_the_last_real_round_of_the_newest_season():
    make_round(2023, 5)
    make_round(2024, 1)
    last = make_round(2024, 2)
    make_round(2024, 3, cancelled=True)

    info = seed()

    assert (info["year"], info["round"]) == (2024, 2)
    assert info["locked"] is False
    qualifying = Session.objects.get(round=last, type=Session.Type.Q)
    race = Session.objects.get(round=last, type=Session.Type.RACE)
    assert qualifying.start_utc > timezone.now() + timedelta(days=1)
    assert race.start_utc > qualifying.start_utc
    assert race.end_utc > race.start_utc
    assert qualifying.status == race.status == Session.Status.SCHEDULED


def test_repeating_it_changes_nothing_but_the_times():
    make_round(2024, 1)
    seed()
    seed()
    assert Session.objects.filter(type=Session.Type.Q).count() == 1
    assert Session.objects.filter(type=Session.Type.RACE).count() == 1


def test_lock_moves_qualifying_into_the_past_and_can_be_undone():
    rnd = make_round(2024, 1)

    assert seed("--lock")["locked"] is True
    assert Session.objects.get(round=rnd, type=Session.Type.Q).start_utc < timezone.now()

    assert seed()["locked"] is False
    assert Session.objects.get(round=rnd, type=Session.Type.Q).start_utc > timezone.now()

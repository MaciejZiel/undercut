"""Helpers for predictions tests. Other modules' rows go through the app registry."""

import datetime as dt
import itertools

from django.apps import apps
from django.contrib.auth import get_user_model

_counter = itertools.count(1)


def _m(name):
    return apps.get_model("catalog", name)


def make_user(name=None, *, verified=True, joined=None):
    n = next(_counter)
    user = get_user_model().objects.create_user(
        username=f"user{n}", email=f"user{n}@example.com", password="pw"
    )
    user.display_name = name or f"Player{n}"
    user.email_verified = verified
    if joined:
        user.date_joined = joined
    user.save()
    return user


def make_driver(name=None):
    n = next(_counter)
    return _m("Driver").objects.create(
        jolpica_id=f"d{n}",
        given_name="Given",
        family_name=name or f"Driver{n}",
        code=f"D{n % 100:02d}",
    )


def make_drivers(count=6):
    return [make_driver() for _ in range(count)]


def make_weekend(year=2025, number=1, *, quali_start=None, with_quali=True):
    """A round with a qualifying session (start_utc=quali_start) and a race session."""
    season, _ = _m("Season").objects.get_or_create(year=year)
    circuit, _ = _m("Circuit").objects.get_or_create(slug="circuit", defaults={"name": "Circuit"})
    round_ = _m("Round").objects.create(
        season=season,
        round=number,
        name=f"GP {number}",
        circuit=circuit,
        date=dt.date(year, 3, number),
    )
    quali = None
    if with_quali:
        quali = _m("Session").objects.create(round=round_, type="Q", start_utc=quali_start)
    race = _m("Session").objects.create(round=round_, type="RACE")
    return round_, quali, race


def constructor():
    return _m("Constructor").objects.get_or_create(slug="team", defaults={"name": "Team"})[0]


def set_race_result(race, podium, *, pole=None, fastest_lap=None, quali=None, extra=()):
    """Replace the race classification: podium = [d1, d2, d3]; extra drivers follow."""
    Result = _m("Result")
    Result.objects.filter(session=race).delete()
    team = constructor()
    drivers = [*podium, *extra]
    for index, driver in enumerate(drivers, start=1):
        Result.objects.create(
            session=race,
            driver=driver,
            constructor=team,
            position=index,
            position_text=str(index),
            grid=1 if driver == pole and quali is None else None,
            fastest_lap_rank=1 if driver == fastest_lap else None,
        )
    if quali is not None:
        _m("QualifyingResult").objects.filter(session=quali).delete()
        if pole is not None:
            _m("QualifyingResult").objects.create(
                session=quali, driver=pole, constructor=team, position=1
            )

"""Factories for standings. Catalog rows are built through the app registry, not imported."""

import factory
from django.apps import apps

from apps.standings.models import ConstructorStanding, DriverStanding


def _catalog(name):
    return apps.get_model("catalog", name)


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Season"
        django_get_or_create = ("year",)

    year = factory.Sequence(lambda n: 2000 + n)


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Driver"

    jolpica_id = factory.Sequence(lambda n: f"driver_{n}")
    given_name = factory.Sequence(lambda n: f"Given{n}")
    family_name = factory.Sequence(lambda n: f"Family{n}")
    code = factory.Sequence(lambda n: f"D{n % 100:02d}")
    nationality = "Dutch"


class ConstructorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Constructor"

    slug = factory.Sequence(lambda n: f"team-{n}")
    jolpica_id = factory.Sequence(lambda n: f"team_{n}")
    name = factory.Sequence(lambda n: f"Team {n}")
    nationality = "British"


class DriverStandingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DriverStanding

    season = factory.SubFactory(SeasonFactory)
    after_round = 1
    driver = factory.SubFactory(DriverFactory)
    position = 1
    position_text = "1"
    points = 25
    wins = 1
    podiums = 1


class ConstructorStandingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConstructorStanding

    season = factory.SubFactory(SeasonFactory)
    after_round = 1
    constructor = factory.SubFactory(ConstructorFactory)
    position = 1
    position_text = "1"
    points = 25
    wins = 1
    podiums = 1

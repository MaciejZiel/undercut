import datetime as dt

import factory

from apps.catalog import models


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Season

    year = factory.Sequence(lambda n: 1950 + n)


class PointsSystemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PointsSystem

    season = factory.SubFactory(SeasonFactory)
    session_type = models.PointsSystem.SessionType.RACE
    points_by_position = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]


class CircuitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Circuit

    slug = factory.Sequence(lambda n: f"circuit-{n}")
    jolpica_id = factory.Sequence(lambda n: f"circuit_{n}")
    name = factory.Sequence(lambda n: f"Circuit {n}")
    timezone = "Europe/Warsaw"


class ConstructorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Constructor

    slug = factory.Sequence(lambda n: f"constructor-{n}")
    jolpica_id = factory.Sequence(lambda n: f"constructor_{n}")
    name = factory.Sequence(lambda n: f"Constructor {n}")


class ConstructorSeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ConstructorSeason

    constructor = factory.SubFactory(ConstructorFactory)
    season = factory.SubFactory(SeasonFactory)


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Driver

    jolpica_id = factory.Sequence(lambda n: f"driver_{n}")
    given_name = factory.Sequence(lambda n: f"Given{n}")
    family_name = factory.Sequence(lambda n: f"Family{n}")


class RoundFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Round

    season = factory.SubFactory(SeasonFactory)
    round = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Grand Prix {n}")
    circuit = factory.SubFactory(CircuitFactory)
    date = dt.date(2025, 3, 16)


class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Session

    round = factory.SubFactory(RoundFactory)
    type = models.Session.Type.RACE


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Result

    session = factory.SubFactory(SessionFactory)
    driver = factory.SubFactory(DriverFactory)
    constructor = factory.SubFactory(ConstructorFactory)
    position = factory.Sequence(lambda n: n + 1)


class QualifyingResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.QualifyingResult

    session = factory.SubFactory(SessionFactory, type=models.Session.Type.Q)
    driver = factory.SubFactory(DriverFactory)
    constructor = factory.SubFactory(ConstructorFactory)
    position = factory.Sequence(lambda n: n + 1)

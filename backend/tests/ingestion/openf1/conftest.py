import datetime as dt
import json
from collections import Counter
from pathlib import Path

import pytest

from apps.ingestion.openf1.client import OpenF1Error
from tests.catalog.factories import (
    CircuitFactory,
    ConstructorFactory,
    DriverFactory,
    ResultFactory,
    RoundFactory,
    SeasonFactory,
    SessionFactory,
)

FIXTURES = Path(__file__).parent / "fixtures"
T0 = dt.datetime(2024, 3, 2, 15, 0, tzinfo=dt.UTC)
RACE_KEY = 9472
NOW = dt.datetime(2024, 6, 1, tzinfo=dt.UTC)


def load(name: str) -> list[dict]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeClient:
    """Serves the recorded Bahrain 2024 fixtures and honours the date window filters."""

    def __init__(self, fail: dict[str, Exception] | None = None, hook=None):
        self.hook = hook
        self.requests = 0
        self.by_endpoint: Counter = Counter()
        self.calls: list[tuple[str, dict]] = []
        self.fail = fail or {}

    def get(self, endpoint, params=None):
        params = dict(params or {})
        self.requests += 1
        self.by_endpoint[endpoint] += 1
        self.calls.append((endpoint, params))
        if self.hook:
            self.hook(endpoint, params, self)
        if endpoint in self.fail:
            raise self.fail[endpoint]
        rows = load(endpoint)
        if "session_key" in params and endpoint == "sessions":
            rows = [r for r in rows if r["session_key"] == params["session_key"]]
        lo, hi = params.get("date>="), params.get("date<")
        if lo or hi:
            rows = [
                r
                for r in rows
                if (not lo or r["date"][:19] >= lo) and (not hi or r["date"][:19] < hi)
            ]
        return rows


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def failing_client():
    return FakeClient(fail={"laps": OpenF1Error("boom", status=500)})


@pytest.fixture
def bahrain(db):
    """Catalog as the Jolpica import leaves it: round, sessions and four known drivers."""
    season = SeasonFactory(year=2024)
    circuit = CircuitFactory(
        name="Bahrain International Circuit", locality="Sakhir", country="Bahrain"
    )
    rnd = RoundFactory(
        season=season,
        round=1,
        name="Bahrain Grand Prix",
        circuit=circuit,
        date=dt.date(2024, 3, 2),
    )
    race = SessionFactory(
        round=rnd,
        type="RACE",
        status="results_final",
        start_utc=T0,
        end_utc=T0 + dt.timedelta(hours=2),
    )
    quali = SessionFactory(
        round=rnd,
        type="Q",
        status="results_final",
        start_utc=dt.datetime(2024, 3, 1, 16, 0, tzinfo=dt.UTC),
        end_utc=dt.datetime(2024, 3, 1, 17, 0, tzinfo=dt.UTC),
    )
    team = ConstructorFactory()
    drivers = {
        "VER": DriverFactory(jolpica_id="max_verstappen", family_name="Verstappen", code="VER"),
        # no code on file: must be found by surname
        "PER": DriverFactory(jolpica_id="perez", given_name="Sergio", family_name="Pérez", code=""),
        "SAI": DriverFactory(jolpica_id="sainz", family_name="Sainz", code="SAI"),
        "LEC": DriverFactory(jolpica_id="leclerc", family_name="Leclerc", code="LEC"),
    }
    for position, driver in enumerate(drivers.values(), start=1):
        ResultFactory(session=race, driver=driver, constructor=team, position=position)
    return {"round": rnd, "race": race, "quali": quali, "drivers": drivers}

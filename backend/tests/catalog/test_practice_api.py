import datetime as dt

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Session

from . import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def round_():
    return f.RoundFactory(season=f.SeasonFactory(year=2026), round=17)


def url(session):
    return f"/api/v1/rounds/2026/17/results/?session={session}"


def test_practice_results_have_best_lap_gap_and_laps(client, round_):
    fp1 = f.SessionFactory(round=round_, type=Session.Type.FP1, status="results_final")
    team = f.ConstructorFactory(name="McLaren")
    f.ResultFactory(session=fp1, position=1, best_lap_ms=92_274, laps=28, constructor=team)
    f.ResultFactory(session=fp1, position=2, best_lap_ms=92_472, laps=26, constructor=team)
    f.ResultFactory(session=fp1, position=3, best_lap_ms=None, laps=2, constructor=team)
    body = client.get(url("FP1")).json()
    assert body["session"] == {"type": "FP1", "status": "results_final"}
    rows = body["results"]
    assert [r["position"] for r in rows] == [1, 2, 3]
    assert [r["gap_ms"] for r in rows] == [0, 198, None]
    assert rows[0]["best_lap_ms"] == 92_274 and rows[0]["laps"] == 28
    assert rows[0]["team"]["name"] == "McLaren"
    assert "points" not in rows[0] and "grid" not in rows[0]


def test_unclassified_practice_rows_come_last(client, round_):
    fp2 = f.SessionFactory(round=round_, type=Session.Type.FP2)
    f.ResultFactory(session=fp2, position=None, best_lap_ms=None)
    f.ResultFactory(session=fp2, position=1, best_lap_ms=90_000)
    rows = client.get(url("FP2")).json()["results"]
    assert [r["position"] for r in rows] == [1, None]


def test_a_practice_session_that_does_not_exist_is_404(client, round_):
    assert client.get(url("FP3")).status_code == 404


def test_sprint_qualifying_uses_the_qualifying_shape_with_sq_labels(client, round_):
    sq = f.SessionFactory(round=round_, type=Session.Type.SQ)
    f.QualifyingResultFactory(session=sq, position=1, q1_ms=91_000, q2_ms=90_500, q3_ms=90_000)
    f.QualifyingResultFactory(session=sq, position=2, q1_ms=91_200, q2_ms=90_700, q3_ms=None)
    f.QualifyingResultFactory(session=sq, position=3, q1_ms=91_900, q2_ms=None, q3_ms=None)
    rows = client.get(url("SQ")).json()["results"]
    assert [r["eliminated_in"] for r in rows] == [None, "SQ2", "SQ1"]
    assert rows[0]["q3_ms"] == 90_000


def test_round_page_marks_practice_sessions_with_results(client, round_):
    fp1 = f.SessionFactory(
        round=round_, type=Session.Type.FP1, start_utc=dt.datetime(2026, 10, 9, 8, tzinfo=dt.UTC)
    )
    f.SessionFactory(round=round_, type=Session.Type.FP2)
    f.ResultFactory(session=fp1, position=1, best_lap_ms=90_000)
    sessions = {
        s["type"]: s["has_results"]
        for s in client.get("/api/v1/rounds/2026/17/").json()["sessions"]
    }
    assert sessions == {"FP1": True, "FP2": False}


def test_unknown_session_codes_are_rejected(client, round_):
    assert client.get(url("FP9")).status_code == 400

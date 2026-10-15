import pytest

from apps.catalog.models import Round, Session
from apps.ingestion.models import DriverNumberMap
from apps.ingestion.openf1 import matching
from apps.ingestion.openf1 import schemas as s
from tests.catalog.factories import CircuitFactory, DriverFactory, RoundFactory

from .conftest import load

pytestmark = pytest.mark.django_db


def meetings():
    return s.Meeting.parse_all(load("meetings"))


def sessions():
    return s.Session.parse_all(load("sessions"))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Practice 1", "FP1"),
        ("Practice 3", "FP3"),
        ("Qualifying", "Q"),
        ("Race", "RACE"),
        ("Sprint", "SPRINT"),
        ("Sprint Qualifying", "SQ"),
        ("Sprint Shootout", "SQ"),
        ("Day 1", None),
        (None, None),
    ],
)
def test_session_type_mapping(name, expected):
    assert matching.session_type_for(name) == expected


def test_matches_round_and_sessions_and_stores_keys(bahrain):
    result = matching.match_year(2024, meetings(), sessions())
    assert result.errors == []
    assert {m.type: m.session_key for m in result.sessions} == {"RACE": 9472, "Q": 9468}
    assert Round.objects.get(pk=bahrain["round"].pk).openf1_meeting_key == 1229
    assert Session.objects.get(pk=bahrain["race"].pk).openf1_session_key == 9472
    assert Session.objects.get(pk=bahrain["quali"].pk).openf1_session_key == 9468
    assert any("Practice 1" in n for n in result.notes)  # no FP session in the catalog: a note
    again = matching.match_year(2024, meetings(), sessions())
    assert again.keys_set == 0 and again.errors == []


def test_date_tolerance_is_three_days(bahrain):
    Round.objects.filter(pk=bahrain["round"].pk).update(date="2024-03-05")
    assert matching.match_year(2024, meetings(), sessions()).errors == []
    Round.objects.filter(pk=bahrain["round"].pk).update(date="2024-03-09")
    result = matching.match_year(2024, meetings(), sessions())
    assert [e["type"] for e in result.errors] == ["unmatched_meeting"]


def test_country_must_match_unless_location_does(bahrain):
    bahrain["round"].circuit.country = "Qatar"
    bahrain["round"].circuit.locality = "Lusail"
    bahrain["round"].circuit.name = "Lusail"
    bahrain["round"].circuit.save()
    bahrain["round"].name = "Qatar Grand Prix"
    bahrain["round"].save()
    result = matching.match_year(2024, meetings(), sessions())
    assert result.errors[0]["type"] == "unmatched_meeting"
    assert Round.objects.get(pk=bahrain["round"].pk).openf1_meeting_key is None


def test_country_alias(bahrain):
    meeting = s.Meeting(
        meeting_key=5,
        meeting_name="Miami Grand Prix",
        country_name="United States",
        location="Miami",
        date_end="2024-03-03T00:00:00+00:00",
    )
    rnd = RoundFactory(
        season=bahrain["round"].season,
        round=2,
        name="Miami Grand Prix",
        circuit=CircuitFactory(country="USA"),
        date="2024-03-03",
    )
    found, _ = matching.match_meeting(meeting, [matching.catalog.season_rounds(2024)[-1]])
    assert found.id == rnd.id


def test_cancelled_and_testing_meetings_are_skipped_quietly(bahrain):
    extra = [
        s.Meeting(
            meeting_key=1, meeting_name="Pre-Season Testing", date_end="2024-02-23T00:00:00Z"
        ),
        s.Meeting(meeting_key=2, meeting_name="Imola", is_cancelled=True),
    ]
    result = matching.match_year(2024, extra, [])
    assert result.errors == [] and len(result.notes) == 2


def test_existing_different_key_is_reported_not_overwritten(bahrain):
    Round.objects.filter(pk=bahrain["round"].pk).update(openf1_meeting_key=777)
    result = matching.match_year(2024, meetings(), sessions())
    assert [e["type"] for e in result.errors] == ["meeting_key_conflict"]
    assert Round.objects.get(pk=bahrain["round"].pk).openf1_meeting_key == 777


def test_missing_race_session_in_catalog_is_an_error(bahrain):
    Session.objects.filter(pk=bahrain["race"].pk).delete()
    result = matching.match_year(2024, meetings(), sessions())
    assert [e["type"] for e in result.errors] == ["unmatched_session"]


def test_drivers_by_code_then_surname_and_unmatched(bahrain):
    drivers = s.Driver.parse_all(load("drivers"))
    res = matching.resolve_drivers(2024, drivers)
    d = bahrain["drivers"]
    assert res.mapping == {1: d["VER"].id, 11: d["PER"].id, 55: d["SAI"].id, 16: d["LEC"].id}
    assert res.created == 4
    assert len(res.unmatched) == 16
    assert {u["name_acronym"] for u in res.unmatched} >= {"HAM", "NOR", "SAR"}
    assert all(u["type"] == "unmatched_driver" for u in res.unmatched)
    assert DriverNumberMap.objects.filter(season_year=2024).count() == 4


def test_admin_fix_in_driver_number_map_is_used_and_kept(bahrain):
    ham = DriverFactory(jolpica_id="hamilton", family_name="Hamilton", code="XXX")
    drivers = s.Driver.parse_all(load("drivers"))
    assert 44 not in matching.resolve_drivers(2024, drivers).mapping
    DriverNumberMap.objects.create(season_year=2024, driver_number=44, driver=ham)
    # a wrong automatic guess is never silently replaced either
    DriverNumberMap.objects.filter(driver_number=1).update(driver=ham)
    res = matching.resolve_drivers(2024, drivers)
    assert res.mapping[44] == ham.id and res.mapping[1] == ham.id
    assert len(res.unmatched) == 15


def test_ambiguous_code_is_not_guessed(bahrain):
    DriverFactory(jolpica_id="a", family_name="Alpha", code="ZZZ")
    DriverFactory(jolpica_id="b", family_name="Beta", code="ZZZ")
    row = s.Driver(driver_number=9, name_acronym="ZZZ", last_name="Unknownson")
    res = matching.resolve_drivers(2024, [row])
    assert res.mapping == {} and len(res.unmatched) == 1

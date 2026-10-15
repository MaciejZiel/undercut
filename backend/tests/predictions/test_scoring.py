import pytest

from apps.predictions import config
from apps.predictions.scoring import Outcome, Pick, score_prediction

PICK = Pick(p1=1, p2=2, p3=3, pole=4, fastest_lap=5)


def score(outcome, pick=PICK):
    return score_prediction(pick, outcome)


def test_perfect_prediction_gets_the_maximum():
    result = score(Outcome(p1=1, p2=2, p3=3, pole=4, fastest_lap=5))
    assert result.points == config.MAX_POINTS == 25
    assert result.breakdown == {
        "p1": 5,
        "p2": 5,
        "p3": 5,
        "pole": 3,
        "fastest_lap": 2,
        "exact_podium_bonus": 5,
        "exact_hits": 3,
        "exact_podium": True,
        "pole_hit": True,
        "total": 25,
    }


def test_nothing_right_scores_zero():
    result = score(Outcome(p1=10, p2=11, p3=12, pole=13, fastest_lap=14))
    assert result.points == 0
    assert result.breakdown["exact_hits"] == 0
    assert result.breakdown["exact_podium"] is False
    assert result.breakdown["pole_hit"] is False


def test_driver_on_podium_in_wrong_position_gets_two():
    result = score(Outcome(p1=2, p2=1, p3=3, pole=13, fastest_lap=14))
    assert result.breakdown["p1"] == 2
    assert result.breakdown["p2"] == 2
    assert result.breakdown["p3"] == 5
    assert result.points == 9
    assert result.breakdown["exact_hits"] == 1
    assert result.breakdown["exact_podium_bonus"] == 0


def test_all_three_right_drivers_wrong_order_no_bonus():
    result = score(Outcome(p1=3, p2=1, p3=2, pole=None, fastest_lap=None))
    assert result.points == 6
    assert result.breakdown["exact_podium"] is False


def test_bonus_only_with_exact_order():
    result = score(Outcome(p1=1, p2=2, p3=3, pole=13, fastest_lap=14))
    assert result.points == 15 + 5


def test_pole_and_fastest_lap_separately():
    assert score(Outcome(p1=9, p2=9, p3=9, pole=4, fastest_lap=14)).points == 3
    assert score(Outcome(p1=9, p2=9, p3=9, pole=13, fastest_lap=5)).points == 2


def test_missing_pole_and_fastest_lap_are_not_scored():
    result = score(Outcome(p1=1, p2=2, p3=3))
    assert result.breakdown["pole"] is None
    assert result.breakdown["fastest_lap"] is None
    assert result.breakdown["pole_hit"] is False
    assert result.points == 20


def test_missing_podium_position_is_not_scored_but_others_are():
    result = score(Outcome(p1=1, p2=None, p3=3, pole=4))
    assert result.breakdown["p2"] is None
    assert result.breakdown["p1"] == 5
    assert result.breakdown["exact_podium"] is False
    assert result.points == 5 + 5 + 3


def test_pick_matching_a_missing_slot_driver_on_other_slot_counts_as_podium():
    # picked P1 (1) finished P2 while P1 is known to be 3
    result = score(Outcome(p1=3, p2=1, p3=None))
    assert result.breakdown["p1"] == 2
    assert result.breakdown["p3"] is None


def test_empty_outcome_is_unscored():
    assert score(Outcome()) is None
    assert Outcome().is_empty


def test_only_pole_known_is_scored():
    result = score(Outcome(pole=4))
    assert result.points == 3


def test_rescoring_after_a_disqualification_is_idempotent_and_corrects_points():
    before = Outcome(p1=1, p2=2, p3=3, pole=4, fastest_lap=5)
    # driver 1 disqualified: 2, 3, 7 move up
    after = Outcome(p1=2, p2=3, p3=7, pole=4, fastest_lap=5)
    first = score(before)
    corrected = score(after)
    assert corrected.points != first.points
    assert score(after) == corrected
    assert score(before) == first
    assert corrected.breakdown["p1"] == 0 and corrected.breakdown["p3"] == 2


@pytest.mark.parametrize("slot", ["p1", "p2", "p3"])
def test_each_slot_exact_is_five(slot):
    kwargs = {"p1": 9, "p2": 9, "p3": 9}
    kwargs[slot] = getattr(PICK, slot)
    assert score(Outcome(**kwargs)).breakdown[slot] == 5

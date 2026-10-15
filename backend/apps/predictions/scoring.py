"""Pure scoring of one prediction against a race outcome (no Django, no I/O).

Missing data is never scored: an unknown pole or fastest lap gives no points and is reported as
None in the breakdown. When nothing at all is known about the race the prediction is unscored
(`score_prediction` returns None), so a correction that arrives later simply re-runs it.
Scoring is a pure function of (pick, outcome): re-scoring after a result correction (for example
a disqualification) is idempotent by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config

PODIUM_SLOTS = ("p1", "p2", "p3")


@dataclass(frozen=True)
class Pick:
    p1: int
    p2: int
    p3: int
    pole: int
    fastest_lap: int


@dataclass(frozen=True)
class Outcome:
    """Driver ids of the real result; None where the data is missing."""

    p1: int | None = None
    p2: int | None = None
    p3: int | None = None
    pole: int | None = None
    fastest_lap: int | None = None

    @property
    def podium(self) -> tuple[int | None, int | None, int | None]:
        return (self.p1, self.p2, self.p3)

    @property
    def is_empty(self) -> bool:
        return all(value is None for value in (*self.podium, self.pole, self.fastest_lap))


@dataclass(frozen=True)
class Score:
    points: int
    breakdown: dict


def score_prediction(pick: Pick, outcome: Outcome) -> Score | None:
    """Score a pick; None when the outcome holds no data at all."""
    if outcome.is_empty:
        return None

    actual_podium = {driver for driver in outcome.podium if driver is not None}
    breakdown: dict = {}
    exact_hits = 0
    for slot in PODIUM_SLOTS:
        picked = getattr(pick, slot)
        actual = getattr(outcome, slot)
        if actual is None:
            breakdown[slot] = None  # unknown position: not scored
        elif picked == actual:
            breakdown[slot] = config.POINTS_EXACT_PODIUM_POSITION
            exact_hits += 1
        elif picked in actual_podium:
            breakdown[slot] = config.POINTS_DRIVER_ON_PODIUM_WRONG_POSITION
        else:
            breakdown[slot] = 0

    pole_hit = outcome.pole is not None and pick.pole == outcome.pole
    fastest_lap_hit = outcome.fastest_lap is not None and pick.fastest_lap == outcome.fastest_lap
    breakdown["pole"] = None if outcome.pole is None else _points(pole_hit, config.POINTS_POLE)
    breakdown["fastest_lap"] = (
        None if outcome.fastest_lap is None else _points(fastest_lap_hit, config.POINTS_FASTEST_LAP)
    )

    exact_podium = exact_hits == len(PODIUM_SLOTS)
    breakdown["exact_podium_bonus"] = _points(exact_podium, config.POINTS_EXACT_PODIUM_BONUS)
    # Counters used by the leaderboard (FR-604) and its tie-break.
    breakdown["exact_hits"] = exact_hits
    breakdown["exact_podium"] = exact_podium
    breakdown["pole_hit"] = pole_hit

    points = sum(
        breakdown[name] or 0
        for name in (*PODIUM_SLOTS, "pole", "fastest_lap", "exact_podium_bonus")
    )
    breakdown["total"] = points
    return Score(points=points, breakdown=breakdown)


def _points(hit: bool, value: int) -> int:
    return value if hit else 0

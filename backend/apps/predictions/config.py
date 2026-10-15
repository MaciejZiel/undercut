"""Tunable rules of the predictions game.

The scoring table is plain constants (no Django import) so `scoring.py` stays trivially testable.
League limits are read from Django settings lazily, with defaults, so they can be overridden
without editing this module.
"""

# Scoring table (FR-603). Maximum: 3 * 5 + 3 + 2 + 5 = 25.
POINTS_EXACT_PODIUM_POSITION = 5
POINTS_DRIVER_ON_PODIUM_WRONG_POSITION = 2
POINTS_POLE = 3
POINTS_FASTEST_LAP = 2
POINTS_EXACT_PODIUM_BONUS = 5
MAX_POINTS = (
    3 * POINTS_EXACT_PODIUM_POSITION
    + POINTS_POLE
    + POINTS_FASTEST_LAP
    + (POINTS_EXACT_PODIUM_BONUS)
)

INVITE_CODE_LENGTH = 8
# No 0/O/1/I/L: codes are typed by hand from a message.
INVITE_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

LEADERBOARD_PAGE_SIZE = 50
LEADERBOARD_MAX_PAGE_SIZE = 100


def _setting(name: str, default):
    from django.conf import settings

    return getattr(settings, name, default)


def max_league_members() -> int:
    return _setting("PREDICTIONS_MAX_LEAGUE_MEMBERS", 50)


def max_leagues_per_user() -> int:
    return _setting("PREDICTIONS_MAX_LEAGUES_PER_USER", 10)

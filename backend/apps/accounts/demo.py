"""Nightly reset of the demo data (FR-507): the demo account, its league and the bot players.

Everything here is a pure function of (today's date, catalog data), so running it twice on one
day leaves the same state. Other modules' rows are reached through their public functions and
through relations declared on our own models (never their model classes).
"""

from __future__ import annotations

import datetime as dt
import logging
import random

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.catalog import selectors as catalog
from apps.catalog import summaries
from apps.predictions import errors as prediction_errors
from apps.predictions import locking, scoring
from apps.predictions import services as prediction_services

from . import services

logger = logging.getLogger(__name__)
User = get_user_model()

BOT_NAMES = ("Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel")
BOT_USERNAME_PREFIX = "demo-bot-"
DEMO_LEAGUE_NAME = "Demo league"
# Not in the invite-code alphabet (it has no O or L), so no random code can collide with it.
DEMO_LEAGUE_CODE = "DEMOLEAG"
SAMPLE_ROUNDS = 3
POOL_SIZE = 10


def ensure_bots() -> list:
    """The bot players: demo accounts without password or e-mail. Created when missing."""
    bots = []
    for index, name in enumerate(BOT_NAMES, start=1):
        username = f"{BOT_USERNAME_PREFIX}{index}"
        display = f"Demo Bot {name}"
        bot = User.objects.filter(username=username).first() or User(username=username)
        bot.is_demo = True
        bot.is_active = True
        bot.is_staff = bot.is_superuser = False
        bot.email = ""
        bot.email_verified = False
        bot.set_unusable_password()
        taken = User.objects.filter(display_name__iexact=display).exclude(pk=bot.pk).exists()
        bot.display_name = None if taken else display
        bot.save()
        bots.append(bot)
    return bots


def ensure_league(owner, bots):
    """The demo league with the demo account and all bots as members."""
    try:
        league = prediction_services.get_league(DEMO_LEAGUE_CODE)
    except prediction_errors.LeagueNotFound:
        league = owner.owned_leagues.create(name=DEMO_LEAGUE_NAME, invite_code=DEMO_LEAGUE_CODE)
    if league.owner_id != owner.pk:
        league.owner = owner
        league.save(update_fields=["owner"])
    for member in (owner, *bots):
        league.memberships.get_or_create(user=member)
    return league


def _picks(rng: random.Random, pool: list[int]) -> dict[str, int] | None:
    if len(pool) < 3:
        return None
    p1, p2, p3 = rng.sample(pool, 3)
    return {
        "p1_id": p1,
        "p2_id": p2,
        "p3_id": p3,
        "pole_id": rng.choice(pool),
        "fastest_lap_id": rng.choice(pool),
    }


def _scored(round_id: int, picks: dict[str, int]) -> dict:
    ids = catalog.race_outcome(round_id)
    outcome = scoring.Outcome(
        p1=ids["podium"][0],
        p2=ids["podium"][1],
        p3=ids["podium"][2],
        pole=ids["pole"],
        fastest_lap=ids["fastest_lap"],
    )
    result = scoring.score_prediction(
        scoring.Pick(
            p1=picks["p1_id"],
            p2=picks["p2_id"],
            p3=picks["p3_id"],
            pole=picks["pole_id"],
            fastest_lap=picks["fastest_lap_id"],
        ),
        outcome,
    )
    return {"points": result.points, "breakdown": result.breakdown} if result else {}


def _pick_for(player, round_id: int, pool: list[int], today: dt.date, *, score: bool) -> None:
    rng = random.Random(f"demo:{today.isoformat()}:{player.username}:{round_id}")
    picks = _picks(rng, pool)
    if picks is None:
        return
    extra = _scored(round_id, picks) if score else {}
    player.predictions.create(round_id=round_id, **picks, **extra)


def reset_demo_data(today: dt.date | None = None) -> None:
    """Reset the demo account, then rebuild the bots' league and everybody's sample picks."""
    demo = services.get_demo_user()
    if demo is None:
        logger.info("No demo account; nothing to reset")
        return
    now = locking.now()
    today = today or now.date()
    with transaction.atomic():
        services.reset_demo_account()
        bots = ensure_bots()
        ensure_league(demo, bots)
        players = [demo, *bots]
        for player in players:
            player.predictions.all().delete()

        completed = summaries.latest_completed_round_ids(SAMPLE_ROUNDS)
        for round_id in completed:  # the demo account's history
            pool = summaries.grid_driver_ids(round_id, POOL_SIZE)
            _pick_for(demo, round_id, pool, today, score=True)
        if not completed:
            return
        last = completed[0]
        last_pool = summaries.grid_driver_ids(last, POOL_SIZE)
        open_rounds = summaries.open_round_ids(now)
        for bot in bots:
            _pick_for(bot, last, last_pool, today, score=True)
            for round_id in open_rounds:
                _pick_for(bot, round_id, last_pool, today, score=False)

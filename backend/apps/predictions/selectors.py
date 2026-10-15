"""Read side of the predictions module: leaderboards, history, picks and statistics."""

from __future__ import annotations

from django.db.models import Count, F, IntegerField, Min, Q, Sum
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, Coalesce

from apps.catalog import selectors as catalog

from . import config, locking
from .models import League, LeagueMembership, Prediction

DELETED_USER = "Deleted user"
SLOTS = ("p1", "p2", "p3", "pole", "fastest_lap")
STATS_PER_SLOT = 10


def display_name(user_id: int | None, name: str | None) -> str:
    if user_id is None:
        return DELETED_USER
    return name or f"Player {user_id}"


def _pick_ids(prediction: Prediction) -> list[int]:
    return [getattr(prediction, f"{slot}_id") for slot in SLOTS]


def _pick_dict(prediction: Prediction, labels: dict[int, dict]) -> dict:
    return {slot: labels.get(getattr(prediction, f"{slot}_id")) for slot in SLOTS}


# --- My pick, round state --------------------------------------------------------------------


def round_state(user, round_: dict) -> dict:
    """Open/closed state of a round and the user's own pick (visible to its owner always)."""
    start = locking.closes_at(round_["id"])
    if start is None:
        status = "unavailable"
    else:
        status = "closed" if locking.now() >= start else "open"
    my_pick = None
    if user is not None and user.is_authenticated:
        prediction = Prediction.objects.filter(user=user, round_id=round_["id"]).first()
        if prediction is not None:
            labels = catalog.driver_labels(_pick_ids(prediction))
            my_pick = {
                **_pick_dict(prediction, labels),
                "points": prediction.points,
                "breakdown": prediction.breakdown,
                "updated_at": prediction.updated_at,
            }
    return {
        "round": {k: round_[k] for k in ("id", "year", "round", "name")},
        "status": status,
        "closes_at": start,
        "my_pick": my_pick,
    }


def history(user) -> list[dict]:
    """The user's picks with the real result and the points breakdown (FR-606)."""
    predictions = list(Prediction.objects.filter(user=user).order_by("-round__date", "-round_id"))
    round_ids = [p.round_id for p in predictions]
    rounds = catalog.round_refs(round_ids)
    outcomes = catalog.race_outcomes(round_ids)
    driver_ids = set()
    for prediction in predictions:
        driver_ids.update(_pick_ids(prediction))
    for outcome in outcomes.values():
        driver_ids.update(
            d for d in (*outcome["podium"], outcome["pole"], outcome["fastest_lap"]) if d
        )
    labels = catalog.driver_labels(driver_ids)
    rows = []
    for prediction in predictions:
        outcome = outcomes[prediction.round_id]
        scored = prediction.points is not None
        rows.append(
            {
                "round": rounds.get(prediction.round_id),
                "pick": _pick_dict(prediction, labels),
                "result": (
                    {
                        "p1": labels.get(outcome["podium"][0]),
                        "p2": labels.get(outcome["podium"][1]),
                        "p3": labels.get(outcome["podium"][2]),
                        "pole": labels.get(outcome["pole"]),
                        "fastest_lap": labels.get(outcome["fastest_lap"]),
                    }
                    if scored
                    else None
                ),
                "points": prediction.points,
                "breakdown": prediction.breakdown,
            }
        )
    return rows


# --- Leaderboards ----------------------------------------------------------------------------


def latest_scored_year() -> int | None:
    return (
        Prediction.objects.filter(points__isnull=False)
        .order_by("-round__season__year")
        .values_list("round__season__year", flat=True)
        .first()
    )


def leaderboard(
    *,
    season: int | None = None,
    round_number: int | None = None,
    league: League | None = None,
    limit: int = config.LEADERBOARD_PAGE_SIZE,
    offset: int = 0,
) -> dict:
    """Ranking by points; ties by more exact hits, more correct poles, earlier registration.

    Two queries (page and total) however many players there are. Deleted accounts are shown as
    "Deleted user", one row per prediction (their identity is gone, so they cannot be merged).
    """
    if season is None:
        season = latest_scored_year()
    queryset = Prediction.objects.filter(points__isnull=False)
    if season is not None:
        queryset = queryset.filter(round__season__year=season)
        if round_number is not None:
            queryset = queryset.filter(round__round=round_number)
    if league is not None:
        queryset = queryset.filter(user__league_memberships__league_id=league.pk)
    else:
        # The demo account and its bots only exist to fill the demo league, never the global table.
        # (exclude keeps rows of deleted users, whose user is NULL.)
        queryset = queryset.exclude(user__is_demo=True)

    grouped = (
        queryset.annotate(player=Coalesce(F("user_id"), -F("id")))
        .values("player", "user_id", "user__display_name")
        .annotate(
            total=Sum("points"),
            exact_hits=Coalesce(Sum(Cast(KT("breakdown__exact_hits"), IntegerField())), 0),
            pole_hits=Count("id", filter=Q(breakdown__pole_hit=True)),
            exact_podiums=Count("id", filter=Q(breakdown__exact_podium=True)),
            predictions=Count("id"),
            registered=Min(Coalesce("user__date_joined", "created_at")),
        )
        .order_by("-total", "-exact_hits", "-pole_hits", "registered", "player")
    )
    count = grouped.count()
    results = [
        {
            "rank": offset + index + 1,
            "user_id": row["user_id"],
            "name": display_name(row["user_id"], row["user__display_name"]),
            "points": row["total"],
            "exact_hits": row["exact_hits"],
            "pole_hits": row["pole_hits"],
            "exact_podiums": row["exact_podiums"],
            "predictions": row["predictions"],
        }
        for index, row in enumerate(grouped[offset : offset + limit])
    ]
    return {"season": season, "round": round_number, "count": count, "results": results}


# --- Leagues ---------------------------------------------------------------------------------


def my_leagues(user) -> list[dict]:
    mine = LeagueMembership.objects.filter(user=user).values("league_id")
    leagues = League.objects.filter(id__in=mine).annotate(member_count=Count("memberships"))
    return [
        {
            "name": league.name,
            "invite_code": league.invite_code,
            "is_owner": league.owner_id == user.pk,
            "member_count": league.member_count,
        }
        for league in leagues
    ]


def league_detail(league: League, user) -> dict:
    members = [
        {
            "user_id": row["user_id"],
            "name": display_name(row["user_id"], row["user__display_name"]),
            "joined_at": row["joined_at"],
        }
        for row in league.memberships.values("user_id", "user__display_name", "joined_at")
    ]
    return {
        "name": league.name,
        "invite_code": league.invite_code,
        "owner_id": league.owner_id,
        "is_owner": league.owner_id == user.pk,
        "member_count": len(members),
        "max_members": config.max_league_members(),
        "members": members,
    }


def league_picks(league: League, round_: dict) -> list[dict]:
    """Every member's pick for a round; only after the lock."""
    locking.assert_picks_visible(round_["id"])
    predictions = list(
        Prediction.objects.filter(
            round_id=round_["id"], user__league_memberships__league_id=league.pk
        )
        .select_related("user")
        .order_by("-points", "id")
    )
    driver_ids = {d for p in predictions for d in _pick_ids(p)}
    labels = catalog.driver_labels(driver_ids)
    return [
        {
            "user_id": p.user_id,
            "name": display_name(p.user_id, p.user.display_name if p.user else None),
            "pick": _pick_dict(p, labels),
            "points": p.points,
            "breakdown": p.breakdown,
        }
        for p in predictions
    ]


# --- Global statistics -----------------------------------------------------------------------


def pick_stats(round_: dict) -> dict:
    """Share of players per driver for each slot ("62% picked X for P1"); only after the lock."""
    locking.assert_picks_visible(round_["id"])
    queryset = Prediction.objects.filter(round_id=round_["id"])
    total = queryset.count()
    raw: dict[str, list[tuple[int, int]]] = {}
    for slot in SLOTS:
        rows = (
            queryset.values(f"{slot}_id")
            .annotate(n=Count("id"))
            .order_by("-n", f"{slot}_id")[:STATS_PER_SLOT]
        )
        raw[slot] = [(row[f"{slot}_id"], row["n"]) for row in rows]
    labels = catalog.driver_labels({driver for rows in raw.values() for driver, _ in rows})
    slots = {
        slot: [
            {
                "driver": labels.get(driver),
                "count": n,
                "percent": round(100 * n / total, 1),
            }
            for driver, n in rows
        ]
        for slot, rows in raw.items()
    }
    return {
        "round": {k: round_[k] for k in ("id", "year", "round", "name")},
        "total": total,
        "slots": slots,
    }

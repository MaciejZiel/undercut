"""Write side of the predictions module: picks, scoring and leagues."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.catalog import selectors as catalog
from apps.events.publisher import publish

from . import config, errors, locking, scoring
from .models import League, LeagueMembership, Prediction, generate_invite_code

PREDICTIONS_SCORED = "PredictionsScored"


def resolve_round(year: int, number: int) -> dict:
    found = catalog.find_round(year, number)
    if found is None:
        raise errors.RoundNotFound(f"Round {number} of {year} does not exist.")
    return found


# --- Predictions ----------------------------------------------------------------------------


@dataclass(frozen=True)
class PickInput:
    p1: int
    p2: int
    p3: int
    pole: int
    fastest_lap: int

    def ids(self) -> tuple[int, ...]:
        return (self.p1, self.p2, self.p3, self.pole, self.fastest_lap)


def submit_prediction(user, year: int, number: int, pick: PickInput) -> tuple[Prediction, bool]:
    """Create or update the user's prediction. Returns (prediction, created)."""
    if not user.email_verified:
        raise errors.EmailNotVerified()
    round_ = resolve_round(year, number)
    if round_["is_cancelled"]:
        raise errors.RoundCancelled()
    start = locking.closes_at(round_["id"])
    if start is None:
        raise errors.QualifyingTimeUnknown()
    if locking.now() >= start:
        raise errors.PredictionsLocked()
    if len({pick.p1, pick.p2, pick.p3}) != 3:
        raise errors.InvalidPrediction("A driver can appear only once on the podium.")
    if catalog.existing_driver_ids(pick.ids()) != set(pick.ids()):
        raise errors.InvalidPrediction("Unknown driver.")

    values = {
        "p1_id": pick.p1,
        "p2_id": pick.p2,
        "p3_id": pick.p3,
        "pole_id": pick.pole,
        "fastest_lap_id": pick.fastest_lap,
    }
    with transaction.atomic():
        prediction, created = Prediction.objects.select_for_update().get_or_create(
            user=user, round_id=round_["id"], defaults=values
        )
        if not created:
            for field, value in values.items():
                setattr(prediction, field, value)
            prediction.points = None
            prediction.breakdown = {}
            prediction.save()
    return prediction, created


def score_round(round_id: int) -> int:
    """Recompute the points of every prediction of a round. Idempotent.

    A pure function of (picks, current result), so running it again after a correction (e.g. a
    disqualification) converges to the right numbers. Returns the number of predictions touched.
    """
    outcome_ids = catalog.race_outcome(round_id)
    outcome = scoring.Outcome(
        p1=outcome_ids["podium"][0],
        p2=outcome_ids["podium"][1],
        p3=outcome_ids["podium"][2],
        pole=outcome_ids["pole"],
        fastest_lap=outcome_ids["fastest_lap"],
    )
    with transaction.atomic():
        predictions = list(Prediction.objects.select_for_update().filter(round_id=round_id))
        for prediction in predictions:
            result = scoring.score_prediction(
                scoring.Pick(
                    p1=prediction.p1_id,
                    p2=prediction.p2_id,
                    p3=prediction.p3_id,
                    pole=prediction.pole_id,
                    fastest_lap=prediction.fastest_lap_id,
                ),
                outcome,
            )
            prediction.points = result.points if result else None
            prediction.breakdown = result.breakdown if result else {}
        Prediction.objects.bulk_update(predictions, ["points", "breakdown"])
    return len(predictions)


def score_round_and_publish(round_id: int) -> int:
    """Score a round and announce it, in one transaction (the event commits with the data)."""
    with transaction.atomic():
        count = score_round(round_id)
        publish(PREDICTIONS_SCORED, key=f"round:{round_id}", payload={"round_id": round_id})
    return count


# --- Leagues -------------------------------------------------------------------------------


def normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def _new_code() -> str:
    for _ in range(10):
        code = generate_invite_code()
        if not League.objects.filter(invite_code=code).exists():
            return code
    raise RuntimeError("Could not generate a unique invite code")  # pragma: no cover


def _league_count(user) -> int:
    return LeagueMembership.objects.filter(user=user).count()


def create_league(user, name: str) -> League:
    name = (name or "").strip()
    if not name:
        raise errors.InvalidPrediction("League name is required.")
    with transaction.atomic():
        # Serialise per user so the limit cannot be raced past.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if _league_count(user) >= config.max_leagues_per_user():
            raise errors.LeagueLimitReached()
        for _ in range(5):
            try:
                with transaction.atomic():
                    league = League.objects.create(name=name, owner=user, invite_code=_new_code())
                break
            except IntegrityError:  # pragma: no cover - code collision between check and insert
                continue
        else:  # pragma: no cover
            raise RuntimeError("Could not create a league")
        LeagueMembership.objects.create(league=league, user=user)
    return league


def get_league(code: str) -> League:
    league = League.objects.filter(invite_code=normalize_code(code)).first()
    if league is None:
        raise errors.LeagueNotFound()
    return league


def join_league(user, code: str) -> League:
    with transaction.atomic():
        league = League.objects.select_for_update().filter(invite_code=normalize_code(code)).first()
        if league is None:
            raise errors.LeagueNotFound()
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if LeagueMembership.objects.filter(league=league, user=user).exists():
            raise errors.AlreadyMember()
        if league.memberships.count() >= config.max_league_members():
            raise errors.LeagueFull()
        if _league_count(user) >= config.max_leagues_per_user():
            raise errors.LeagueLimitReached()
        LeagueMembership.objects.create(league=league, user=user)
    return league


def require_member(user, league: League) -> None:
    if not LeagueMembership.objects.filter(league=league, user=user).exists():
        raise errors.NotLeagueMember()


def _require_owner(user, league: League) -> None:
    if league.owner_id is None or league.owner_id != user.pk:
        raise errors.NotLeagueOwner()


def remove_member(owner, code: str, user_id: int) -> None:
    league = get_league(code)
    _require_owner(owner, league)
    if user_id == owner.pk:
        raise errors.OwnerCannotLeave("The owner cannot be removed; delete the league instead.")
    deleted, _ = LeagueMembership.objects.filter(league=league, user_id=user_id).delete()
    if not deleted:
        raise errors.NotLeagueMember("This user is not a member of the league.")


def leave_league(user, code: str) -> None:
    league = get_league(code)
    if league.owner_id == user.pk:
        raise errors.OwnerCannotLeave()
    deleted, _ = LeagueMembership.objects.filter(league=league, user=user).delete()
    if not deleted:
        raise errors.NotLeagueMember()


def renew_code(owner, code: str) -> League:
    league = get_league(code)
    _require_owner(owner, league)
    league.invite_code = _new_code()
    league.save(update_fields=["invite_code"])
    return league


def delete_league(owner, code: str) -> None:
    league = get_league(code)
    _require_owner(owner, league)
    league.delete()

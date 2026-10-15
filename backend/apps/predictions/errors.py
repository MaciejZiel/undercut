"""Domain errors of the predictions module. The API layer maps them to HTTP statuses."""


class PredictionsError(Exception):
    code = "predictions_error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.__doc__ or self.code)


class RoundNotFound(PredictionsError):
    """Round not found."""

    code = "round_not_found"


class RoundCancelled(PredictionsError):
    """This round was cancelled."""

    code = "round_cancelled"


class QualifyingTimeUnknown(PredictionsError):
    """The qualifying start time of this round is not known yet, so the lock time is undefined."""

    code = "qualifying_time_unknown"


class PredictionsLocked(PredictionsError):
    """Predictions for this round are closed (qualifying has started)."""

    code = "predictions_locked"


class PicksHidden(PredictionsError):
    """Other players' picks are visible only after predictions close."""

    code = "picks_hidden"


class EmailNotVerified(PredictionsError):
    """Verify your e-mail address before making predictions."""

    code = "email_not_verified"


class InvalidPrediction(PredictionsError):
    """Invalid prediction."""

    code = "invalid_prediction"


class LeagueNotFound(PredictionsError):
    """League not found."""

    code = "league_not_found"


class NotLeagueMember(PredictionsError):
    """You are not a member of this league."""

    code = "not_league_member"


class NotLeagueOwner(PredictionsError):
    """Only the league owner can do this."""

    code = "not_league_owner"


class AlreadyMember(PredictionsError):
    """You are already a member of this league."""

    code = "already_member"


class LeagueFull(PredictionsError):
    """This league is full."""

    code = "league_full"


class LeagueLimitReached(PredictionsError):
    """You have reached the maximum number of leagues."""

    code = "league_limit_reached"


class OwnerCannotLeave(PredictionsError):
    """The owner cannot leave the league; delete it instead."""

    code = "owner_cannot_leave"

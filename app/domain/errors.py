"""Domain-level errors.

Phase 2 will map these onto HTTP status codes; the domain layer itself stays
free of any web concern.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every rule violation the domain refuses."""


class EditWindowClosed(DomainError):
    """The date is older than yesterday in the user's timezone.

    The past is immutable: today and yesterday are editable, nothing else.
    """


class InvalidPin(DomainError):
    """The proposed PIN does not match the configured format.

    Raised when *setting* a PIN, never when checking one: a wrong guess at login
    is an expected outcome, not an error.
    """


class NotFound(DomainError):
    """The requested record does not exist on this user's board.

    Also raised when a record exists but belongs to someone else: boards are
    fully separate, so "not yours" and "not there" are deliberately
    indistinguishable from the outside.
    """


class HabitNotFound(NotFound):
    """No such habit on this user's board."""


class BucketNotFound(NotFound):
    """No such bucket on this user's board."""


class HabitNotOwned(DomainError):
    """The habit belongs to a different user. Boards are fully separate."""


class HabitInactive(DomainError):
    """The habit is archived, so it can no longer be scheduled or ticked."""


class HabitNotScheduled(DomainError):
    """No fact row exists for this (user, habit, date).

    Completing something that was not expected today is a bonus; use
    :func:`app.domain.tracking.add_bonus`.
    """


class HabitAlreadyScheduled(DomainError):
    """The habit *was* scheduled on this date, so it cannot be a bonus.

    Use :func:`app.domain.tracking.complete_habit` instead.
    """


class DateOutOfRange(DomainError):
    """The date is not present in `dim_date`, so no fact can reference it."""

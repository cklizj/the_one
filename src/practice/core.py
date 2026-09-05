"""Pure scheduling and stats logic.

No I/O and no CLI imports: every function here is unit-testable in isolation.
"""
from __future__ import annotations

import datetime as dt

RATING_INTERVALS_DAYS: dict[str, int] = {
    "again": 1,
    "hard": 3,
    "good": 7,
    "easy": 14,
}
VALID_RATINGS = frozenset(RATING_INTERVALS_DAYS)
DEFAULT_GRACE = dt.timedelta(days=1)


def interval_days(rating: str) -> int:
    """Days until the next review for a rating (the fixed interval table)."""
    try:
        return RATING_INTERVALS_DAYS[rating]
    except KeyError:
        raise ValueError(
            f"unknown rating {rating!r}; expected one of {sorted(VALID_RATINGS)}"
        ) from None


def next_due(last_attempt_at: dt.datetime, rating: str) -> dt.datetime:
    """Next review is anchored to the *last attempt time*, not today."""
    if last_attempt_at.tzinfo is None:
        raise ValueError("last_attempt_at must be tz-aware")
    return last_attempt_at + dt.timedelta(days=interval_days(rating))


def is_due(
    next_review: dt.datetime | None,
    now_local: dt.datetime,
    grace: dt.timedelta = DEFAULT_GRACE,
) -> bool:
    """Nothing scheduled yet, or next review passed (local time, with grace)."""
    if next_review is None:
        return True
    if next_review.tzinfo is None:
        raise ValueError("next_review must be tz-aware")
    local_next = next_review.astimezone(now_local.tzinfo)
    return local_next <= now_local + grace


def latest_next_review(next_reviews: list[dt.datetime]) -> dt.datetime | None:
    """Latest scheduled review among an item's attempts (the one that counts)."""
    present = [n for n in next_reviews if n is not None]
    return max(present) if present else None
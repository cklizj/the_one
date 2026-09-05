"""Unit tests for the pure scheduling core (no I/O)."""
from __future__ import annotations

import datetime as dt

import pytest

from practice import core

UTC = dt.timezone.utc
LOCAL = dt.timezone(dt.timedelta(hours=8))


def test_interval_days_table():
    assert core.interval_days("again") == 1
    assert core.interval_days("hard") == 3
    assert core.interval_days("good") == 7
    assert core.interval_days("easy") == 14


def test_interval_days_invalid():
    with pytest.raises(ValueError):
        core.interval_days("perfect")


def test_next_due_anchors_to_last_attempt():
    last = dt.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert core.next_due(last, "good") == last + dt.timedelta(days=7)


def test_next_due_requires_aware():
    with pytest.raises(ValueError):
        core.next_due(dt.datetime(2026, 1, 1), "good")


def test_is_due_when_never_scheduled():
    assert core.is_due(None, dt.datetime(2026, 9, 5, tzinfo=LOCAL)) is True


def test_is_due_in_future_not_due():
    now = dt.datetime(2026, 9, 5, 12, 0, tzinfo=LOCAL)
    future = now + dt.timedelta(days=2)
    assert core.is_due(future, now) is False


def test_is_due_past_is_due():
    now = dt.datetime(2026, 9, 5, 12, 0, tzinfo=LOCAL)
    past = now - dt.timedelta(hours=1)
    assert core.is_due(past, now) is True


def test_is_due_within_grace_pulled_in_early():
    now = dt.datetime(2026, 9, 5, 0, 30, tzinfo=LOCAL)
    soon = now + dt.timedelta(minutes=10)
    assert core.is_due(soon, now) is True


def test_is_due_beyond_grace_not_due():
    now = dt.datetime(2026, 9, 5, 0, 30, tzinfo=LOCAL)
    far = now + dt.timedelta(days=2)
    assert core.is_due(far, now) is False


def test_is_due_timezone_conversion():
    # 2026-09-05 20:00 UTC == 2026-09-06 04:00 in +8; compare against a local now
    # that is more than the 1-day grace past it, so it must be due.
    utc_next = dt.datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
    now_local = dt.datetime(2026, 9, 7, 12, 0, tzinfo=LOCAL)
    assert core.is_due(utc_next, now_local) is True


def test_latest_next_review():
    a = dt.datetime(2026, 9, 1, tzinfo=UTC)
    b = dt.datetime(2026, 9, 8, tzinfo=UTC)
    assert core.latest_next_review([a, b, None]) == b
    assert core.latest_next_review([]) is None
    assert core.latest_next_review([None]) is None
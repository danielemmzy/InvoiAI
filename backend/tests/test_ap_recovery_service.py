"""Recovery helpers for the durable AP sweeper.

The sweeper is intentionally conservative: it only touches documents that are
still in an in-progress AP state and whose row has not changed for a full
lease period. Terminal states and human-review states are never retried.
"""

from datetime import UTC, datetime, timedelta

from app.services.ap.recovery_service import (
    RECOVERABLE_STATUSES,
    backoff_seconds,
    dead_letter_state,
    is_stale,
    recovery_step,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def test_recovery_step_routes_matching_and_coding():
    assert recovery_step("validating") == "matching"
    assert recovery_step("matching") == "matching"
    assert recovery_step("coding") == "coding"
    assert recovery_step("awaiting_approval") is None
    assert recovery_step("coding_exception") is None
    assert recovery_step("on_hold") is None


def test_recoverable_statuses_exclude_terminal_and_human_states():
    assert RECOVERABLE_STATUSES == ("validating", "matching", "coding")


def test_is_stale_only_for_recoverable_old_documents():
    old = NOW - timedelta(seconds=901)
    fresh = NOW - timedelta(seconds=899)

    assert is_stale("coding", old, now=NOW, lease_seconds=900)
    assert not is_stale("coding", fresh, now=NOW, lease_seconds=900)
    assert not is_stale("awaiting_approval", old, now=NOW, lease_seconds=900)
    assert not is_stale("coding_exception", old, now=NOW, lease_seconds=900)


def test_is_stale_accepts_iso_strings():
    timestamp = (NOW - timedelta(hours=1)).isoformat()

    assert is_stale("matching", timestamp, now=NOW, lease_seconds=900)


def test_is_stale_ignores_missing_or_invalid_timestamps():
    assert not is_stale("coding", None, now=NOW, lease_seconds=900)
    assert not is_stale("coding", "not-a-date", now=NOW, lease_seconds=900)


def test_backoff_is_exponential_and_capped():
    assert [backoff_seconds(attempt) for attempt in (1, 2, 3, 4, 5, 10)] == [
        60,
        120,
        240,
        480,
        900,
        900,
    ]


def test_dead_letter_moves_failures_to_a_visible_exception_state():
    assert dead_letter_state("coding") == ("coding_exception", "ap_coding_error")
    assert dead_letter_state("matching") == ("match_exception", "ap_recovery_failed")
    assert dead_letter_state("validating") == ("match_exception", "ap_recovery_failed")


def test_ap_recovery_is_registered_in_cron():
    from app.scheduler.periodic_jobs import cron

    names = {job.name for job in cron.jobs}
    assert "ap-recovery" in names

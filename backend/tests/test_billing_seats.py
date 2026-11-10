from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

from app.routers.billing_v2 import seat_summary
from app.services.member_seats import seats_available


def test_seat_summary_counts_unique_active_users_and_separates_pending_invites():
    expires = datetime.now(UTC) + timedelta(days=1)
    members = [
        SimpleNamespace(id="1", user_id="user-a", is_active=True, invite_token=None, invite_expires_at=None),
        SimpleNamespace(id="2", user_id="user-a", is_active=True, invite_token=None, invite_expires_at=None),
        SimpleNamespace(id="3", user_id=None, is_active=False, invite_token="token", invite_expires_at=expires),
        SimpleNamespace(id="4", user_id=None, is_active=False, invite_token=None, invite_expires_at=None),
    ]

    assert seat_summary("free", members) == {
        "included": 1,
        "used": 1,
        "pending": 1,
        "available": 0,
        "unlimited": False,
        "additional_seat_rate": None,
    }


def test_unlimited_seats_are_explicit_and_pending_invites_reserve_capacity():
    assert seat_summary("enterprise", []) == {
        "included": None,
        "used": 0,
        "pending": 0,
        "available": None,
        "unlimited": True,
        "additional_seat_rate": None,
    }
    assert seats_available(active_count=2, pending_count=1, limit=3) is False
    assert seats_available(active_count=2, pending_count=0, limit=3) is True
    assert seats_available(active_count=4, pending_count=0, limit=3) is False


def test_revoked_or_expired_invitations_do_not_reserve_a_seat():
    expired = datetime.now(UTC) - timedelta(days=1)
    members = [
        SimpleNamespace(id="revoked", user_id=None, is_active=False, invite_token=None, invite_expires_at=None),
        SimpleNamespace(id="expired", user_id=None, is_active=False, invite_token="old-token", invite_expires_at=expired),
    ]
    assert seat_summary("free", members)["pending"] == 0

from types import SimpleNamespace

from app.routers.billing_v2 import seat_summary


def test_seat_summary_counts_unique_active_users_and_separates_pending_invites():
    members = [
        SimpleNamespace(id="1", user_id="user-a", is_active=True, invite_token=None),
        SimpleNamespace(id="2", user_id="user-a", is_active=True, invite_token=None),
        SimpleNamespace(id="3", user_id=None, is_active=False, invite_token="token"),
        SimpleNamespace(id="4", user_id=None, is_active=False, invite_token=None),
    ]

    assert seat_summary("free", members) == {
        "included": 1,
        "used": 1,
        "pending": 1,
        "available": 0,
        "additional_seat_rate": None,
    }

from unittest.mock import MagicMock

from app.main import app


def test_signup_password_too_short(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "steven@example.com",
            "password": "12345"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Password must be at least 8 characters"


def test_signup_success(client, mocker):
    fake_supabase = MagicMock()

    fake_response = MagicMock()
    fake_response.user = MagicMock(
        id="user-123",
        email="steven@example.com",
    )

    fake_response.session = MagicMock(
        access_token="access-token",
        refresh_token="refresh-token",
    )

    fake_supabase.auth.sign_up.return_value = fake_response

    mocker.patch(
        "app.routers.auth.get_supabase",
        return_value=fake_supabase,
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "steven@example.com",
            "password": "password123"
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["email"] == "steven@example.com"
    assert body["plan"] == "free"
    assert body["access_token"] == "access-token"
    assert body["refresh_token"] == "refresh-token"
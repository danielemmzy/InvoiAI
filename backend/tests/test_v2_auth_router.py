from unittest.mock import AsyncMock, MagicMock


def test_v2_auth_password_policy(client):
    response = client.post("/api/v2/auth/signup", json={"email":"test@example.com","password":"123"})
    assert response.status_code == 422

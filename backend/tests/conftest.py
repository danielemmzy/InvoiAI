import os

os.environ["OPENAI_API_KEY"] = "test"
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test"
os.environ["SUPABASE_SERVICE_KEY"] = "test"
os.environ["STRIPE_SECRET_KEY"] = "test"
os.environ["STRIPE_WEBHOOK_SECRET"] = "test"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import AuthUser, get_current_user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="test-user",
        email="test@example.com",
        plan="free",
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
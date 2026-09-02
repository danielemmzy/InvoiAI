from pathlib import Path

from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient

# Prefer an explicit test environment when present. CI can inject variables
# directly and therefore does not need a .env.test file.
_TEST_ENV = Path(__file__).resolve().parents[1] / ".env.test"
if _TEST_ENV.exists():
    load_dotenv(_TEST_ENV, override=False)


@pytest.fixture
def client():
    # Import the application lazily so pure unit tests do not require
    # the complete web/runtime dependency graph just to collect tests.
    from app2.main import app
    with TestClient(app) as client:
        yield client

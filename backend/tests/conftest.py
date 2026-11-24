from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

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
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    """Return auth headers for testing authenticated endpoints."""
    return {"X-User-Id": "test-user-123", "X-Org-Id": "test-org-1"}


class _FakeQuery:
    """Minimal Supabase-style query builder used by router tests.

    Supports select/insert/update with equality filters, ordering and limits.
    It is deliberately small and only implements the surface the AP router
    endpoints under test actually call.
    """

    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.rows = database.tables.setdefault(table_name, [])
        self.operation = "select"
        self.payload = None
        self.filters = []
        self.in_filters = []
        self._order = None
        self._limit = None
        self._single = False

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        """Mirror PostgREST's `column=in.(a,b,c)` batch filter."""
        self.in_filters.append((column, {str(value) for value in values}))
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def single(self):
        self._single = True
        return self

    def _matches(self, row):
        if not all(str(row.get(column)) == str(value) for column, value in self.filters):
            return False
        return all(
            str(row.get(column)) in allowed
            for column, allowed in self.in_filters
        )

    def execute(self):
        if self.operation == "insert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            self.rows.extend(rows)
            return SimpleNamespace(data=rows)

        matched = [row for row in self.rows if self._matches(row)]

        if self.operation == "update":
            for row in matched:
                row.update(self.payload)
            return SimpleNamespace(data=matched)

        if self._order:
            column, desc = self._order
            matched.sort(key=lambda row: row.get(column), reverse=desc)
        if self._limit is not None:
            matched = matched[: self._limit]
        if self._single:
            return SimpleNamespace(data=matched[0] if matched else None)
        return SimpleNamespace(data=matched)


class FakeDatabase:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return _FakeQuery(self, name)

    def seed(self, name, *rows):
        self.tables.setdefault(name, []).extend(rows)


@pytest.fixture
def fake_db():
    return FakeDatabase()


@pytest.fixture
def ap_api(client, fake_db, monkeypatch):
    """Run AP router tests against a fake database and a finance user."""
    from app.context import AuthUser, OrganizationContext
    from app.core.auth import get_current_user
    from app.core.enum.database import OrgRole, PlanType
    from app.core.ocm import get_org_context
    from app.core.permissions import MANAGE_FINANCE, VIEW_FINANCE
    from app.main import app
    import app.routers.ap as ap_router

    org_id = UUID("00000000-0000-0000-0000-000000000001")
    user_id = UUID("00000000-0000-0000-0000-000000000002")
    user = AuthUser(
        id=user_id,
        email="finance@example.com",
        org_id=org_id,
        role=OrgRole.OWNER,
    )
    context = OrganizationContext(
        user_id=str(user_id),
        org_id=org_id,
        name="Test Org",
        slug="test-org",
        plan=PlanType.FREE,
        role=OrgRole.OWNER,
        permissions={VIEW_FINANCE, MANAGE_FINANCE},
        document_limit=100,
        default_currency="GBP",
        timezone="Europe/London",
    )

    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_org_context] = lambda: context
    monkeypatch.setattr(ap_router, "db", lambda: fake_db)

    try:
        yield SimpleNamespace(
            client=client,
            db=fake_db,
            context=context,
            org_id=org_id,
            user_id=user_id,
        )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

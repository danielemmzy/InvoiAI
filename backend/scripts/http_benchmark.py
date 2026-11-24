"""Local HTTP benchmark for the authenticated document-list endpoint.

This runs the real FastAPI app behind uvicorn and drives it over a real TCP
socket with httpx, so the numbers include HTTP parsing, middleware, auth
dependencies and thread-pool hand-offs rather than only the handler.

The Supabase backend is replaced with an in-process fake that sleeps for the
configured per-query latency, so "one round trip" costs the same wherever it
happens. No production database is contacted.

Usage:
    python scripts/http_benchmark.py [--latency-ms 25] [--requests 30]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import uvicorn

ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")
GL_ACCOUNT_ID = UUID("00000000-0000-0000-0000-0000000000bb")


def build_fake_backend(latency_ms: float, document_count: int):
    """Fake PostgREST client: every execute() costs one round trip."""

    class Query:
        def __init__(self, database, table_name):
            self.database = database
            self.table_name = table_name
            self.wanted_ids = None

        def select(self, *_args, **_kwargs): return self
        def eq(self, *_args, **_kwargs): return self
        def neq(self, *_args, **_kwargs): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self

        def in_(self, _column, values):
            self.wanted_ids = {str(value) for value in values}
            return self

        def execute(self):
            # Blocking sleep mirrors a synchronous Supabase round trip, which
            # is why the app offloads these calls to a thread pool.
            time.sleep(latency_ms / 1000.0)
            self.database.executed.append(self.table_name)
            return SimpleNamespace(data=self.database.rows_for(self.table_name))

    class Database:
        def __init__(self):
            self.executed: list[str] = []
            self.documents = [
                {
                    "id": str(uuid4()),
                    "org_id": str(ORG_ID),
                    "source": "manual",
                    "document_type": "invoice",
                    "industry": "general",
                    "file_url": "org/doc.pdf",
                    "file_name": "doc.pdf",
                    "file_type": "pdf",
                    "pipeline_stage": "intake",
                    "status": "pending",
                    "capture_overrides": {"account": {"id": str(GL_ACCOUNT_ID)}},
                    "capture_progress": 0,
                }
                for _ in range(document_count)
            ]

        def table(self, name):
            return Query(self, name)

        def rows_for(self, table_name):
            if table_name == "document_line_items":
                return [{"document_id": row["id"], "quantity": 2} for row in self.documents]
            if table_name == "invoice_codings":
                return []
            if table_name == "chart_of_accounts":
                return [
                    {
                        "id": str(GL_ACCOUNT_ID),
                        "account_code": "5000",
                        "account_name": "Office costs",
                    }
                ]
            return []

    return Database()


class FakeDocumentRepository:
    def __init__(self, database):
        self.database = database

    async def list_document_rows(self, org_id, limit=50, offset=0, industry=None, query=None):
        # The real repository returns the page plus an exact count in one call.
        self.database.executed.append("documents")
        return self.database.documents[:limit], len(self.database.documents)


def configure_app(latency_ms: float, document_count: int):
    from app.context import AuthUser, OrganizationContext
    from app.core import auth as auth_module
    from app.core.auth import get_current_user, require_verified_user
    from app.core.enum.database import OrgRole, PlanType
    from app.core.ocm import get_org_context
    from app.core.permissions import VIEW_DOCUMENTS
    from app.main import app
    import app.routers.documents as documents_router

    database = build_fake_backend(latency_ms, document_count)
    round_trip = latency_ms / 1000.0

    user = AuthUser(
        id=uuid4(),
        email="bench@example.com",
        org_id=ORG_ID,
        role=OrgRole.OWNER,
        is_verified=True,
    )
    context = OrganizationContext(
        user_id=str(user.id),
        org_id=ORG_ID,
        name="Bench Org",
        slug="bench-org",
        plan=PlanType.FREE,
        role=OrgRole.OWNER,
        permissions={VIEW_DOCUMENTS},
        document_limit=100,
        default_currency="GBP",
        timezone="Europe/London",
    )

    def fake_validate_token(_token):
        time.sleep(round_trip)
        return user, [], True

    def fake_email_verified(_user_id, *, supabase_verified):
        time.sleep(round_trip)
        return supabase_verified

    def fake_admin_membership(_user_id):
        time.sleep(round_trip)
        return False

    auth_module.validate_token_identity = fake_validate_token
    auth_module.resolve_email_verified = fake_email_verified
    auth_module.mfa_service = SimpleNamespace(has_admin_membership=fake_admin_membership)

    app.dependency_overrides[require_verified_user] = lambda: user
    app.dependency_overrides[get_org_context] = lambda: context
    # get_current_user stays real so token validation, the MFA gate and the
    # two concurrent identity lookups are all inside the measured request.
    app.dependency_overrides.pop(get_current_user, None)

    documents_router.get_container = lambda: SimpleNamespace(
        document_repository=FakeDocumentRepository(database)
    )
    # The router also builds its batched lookups through get_supabase().
    documents_router.get_supabase = lambda: database
    return app, database


def serve(app, port: int):
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        lifespan="off",
        access_log=False,
    )
    server = uvicorn.Server(config)
    # The documents list is rate limited per client address; benchmarking is
    # about latency, so the limiter is switched off for this process only.
    app.state.limiter.enabled = False
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 30
    while not server.started:
        if time.time() > deadline:  # pragma: no cover - startup guard
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.05)
    return server


def measure(port: int, requests: int, database, warmup: int = 5):
    url = f"http://127.0.0.1:{port}/api/v2/documents?offset=0&limit=20"
    headers = {"Authorization": "Bearer benchmark-token"}
    latencies: list[float] = []

    with httpx.Client(timeout=60.0) as client:
        for _ in range(warmup):
            client.get(url, headers=headers)
        # Only the measured requests are counted, so queries-per-request is exact.
        database.executed.clear()
        for _ in range(requests):
            started = time.perf_counter()
            response = client.get(url, headers=headers)
            latencies.append((time.perf_counter() - started) * 1000.0)
            response.raise_for_status()

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[min(len(latencies) - 1, int(round(0.95 * len(latencies))) - 1)]
    return p50, p95, latencies[-1], len(database.executed) / requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latency-ms", type=float, default=25.0)
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    print(
        f"Local HTTP benchmark - document list, {args.latency_ms:.0f} ms per "
        f"simulated Supabase round trip, {args.requests} requests"
    )
    print(f"{'docs':>5} {'q/req':>8} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}")

    for document_count in (1, 20):
        app, database = configure_app(args.latency_ms, document_count)
        server = serve(app, args.port)
        try:
            p50, p95, worst, queries = measure(args.port, args.requests, database)
        finally:
            server.should_exit = True
            time.sleep(0.2)

        print(
            f"{document_count:>5} {queries:>8.1f} {p50:>8.0f} {p95:>8.0f} {worst:>8.0f}"
        )

    print(
        "Note: the Supabase backend is an in-process fake with simulated latency; "
        "no production database was queried."
    )


if __name__ == "__main__":
    main()

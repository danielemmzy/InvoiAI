# V2 Test Run Report

Date: 2026-08-16

## Result

The repository test suite currently contains **28 tests**.

A complete pytest run against the checked-out project source completed with:

```text
28 passed in 0.66s
```

Python used for this verification: Python 3.13.5.

## Important environment note

The execution environment used for this verification could not download the
project's pinned third-party dependencies because outbound package access was
unavailable. The test run therefore used lightweight temporary import stubs
for unavailable infrastructure packages (Supabase, Google client libraries,
OpenAI, Stripe, Redis, SlowAPI, structlog, croniter, and correlation-id).
Those stubs were **not included in the project archive**.

For a real local/CI verification, install `requirements.txt` normally and run:

```powershell
pytest tests/ -v --tb=short
```

The suite was still useful for detecting and fixing actual project defects:
- stale QuickBooks/Xero sync import collisions
- stale notification provider import
- stale V2 auth schema names
- stale usage-service import contract
- OCR pipeline enum/model mismatches
- approval domain ID construction
- finance notification test idempotency fixtures
- token encryption base64url padding handling
- V2 API test assumptions that still expected the removed V1 surface
- cache test assumptions that referenced the old industries router path

No secrets or real credentials are stored in the repository.

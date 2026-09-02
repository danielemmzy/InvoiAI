# V2 Backend Testing

## 1. Install dependencies

```powershell
pip install -r requirements.txt
```

## 2. Configure test environment

Copy `.env.test.example` to `.env.test` and fill in test credentials.
Never commit `.env.test`.

PowerShell:

```powershell
$env:ENV_FILE=".env.test"
pytest tests/ -v --tb=short
```

The application configuration defaults to `.env`; for test runs, either load
`.env.test` into the process environment or use your preferred environment
loader before invoking pytest.

## 3. Required local services

- Redis on `localhost:6379` for cache/rate-limit integration tests.
- Supabase/PostgreSQL for tests that exercise repositories or live workflows.
- Stripe test credentials for Stripe integration tests.

## 4. Test policy

The suite contains deterministic unit tests plus integration tests. Tests that
require external services must use isolated test credentials/data and must not
mutate production data.

Run the complete suite before merging:

```powershell
pytest tests/ -v --tb=short
```

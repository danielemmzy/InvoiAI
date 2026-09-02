# V2 Test Coverage Update

This archive adds focused V2 tests for the backend capabilities that were previously missing from the test suite.

## Added

- `tests/test_v2_ocr_pipeline.py` — OCR persistence, pipeline stage transitions, and analysis hand-off.
- `tests/test_v2_verification_engine.py` — all eight verification modules and recommendation/risk thresholds.
- `tests/test_v2_approval_workflow.py` — approval-step validation and persistence contract.
- `tests/test_v2_quickbooks_worker.py` — active-connection fan-out and one sync invocation per connection.
- `tests/test_v2_insight_analyzers.py` — all six analyzers tolerate an empty organization safely.
- `tests/test_v2_insights.py` — all five detectors and their threshold behavior.
- `tests/test_v2_finance_planning.py` — deterministic allocation math and persistence hand-off.
- `tests/test_v2_copilot_tools.py` — personal tool routing and deterministic planning integration.
- `tests/test_v2_token_refresh_and_retry.py` — `error_count > 3` deactivation and BaseWorker retry behavior.
- `tests/conftest.py` — application import is lazy so unit tests do not require the full FastAPI runtime merely during collection.

## Important verification note

The test suite was syntax-checked successfully in this packaging environment.

A full pytest execution could not be completed here because this runtime does not contain all project dependencies/configuration (`supabase`, `slowapi`, and required environment settings). That is an environment limitation, not a claim that the tests passed.

Run in the project virtual environment after installing the backend requirements:

```powershell
pytest -q
```

## V2 billing note

The current archive contains V1 billing/Stripe routes. A dedicated V2 billing checkout service/router was not invented as part of this test pass because the extracted code does not expose a verified V2 billing contract. That remains a separate migration item rather than a falsely "passing" test.

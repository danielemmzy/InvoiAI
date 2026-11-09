# Provider evidence template

Copy this file to `docs/evidence/<provider>-<yyyy-mm-dd>.md` and fill every
field from a real recorded run. A provider feature is not "tested" by mocking
the adapter. Each provider needs:

1. the provider-contract suite passing in CI (fake HTTP transport), and
2. one recorded run against the provider's real test environment.

| Field | Value |
|---|---|
| Provider | Xero / QuickBooks Online / Sage Business Cloud Accounting |
| Environment | Xero sandbox / QuickBooks sandbox / **Sage trial business** |
| API version | e.g. Xero Accounting 2.0, QuickBooks v3, Sage Accounting 3.1 |
| Test date | YYYY-MM-DD |
| Operator | Name / role |
| App / client ID (reference only) | Never paste the secret or tokens |
| Organization / tenant / realm / business ID | Redacted if shared externally |
| Callback URL registered | Yes/No |

## Resource coverage

| Area | Read | Create | Update | Notes |
|---|---|---|---|---|
| Suppliers / contacts | | | | |
| Chart of accounts | | | | |
| Purchase orders | | | | N/A for Sage |
| Purchase bills / invoices | | | | |
| Purchase credit notes | | | | N/A where the provider has none |
| Status codes / types | | | | Sage only |
| Currencies | | | | |
| Taxes | | | | |
| Settings | | | | |

## Behavioural evidence

Record the observed result, not the expected one.

| Check | Result | Evidence reference |
|---|---|---|
| No provider call before local approval | | |
| Exactly one create call on first attempt | | |
| Timeout after create reconciles to the existing record | | |
| Retry after 5xx succeeds without a duplicate | | |
| 4xx stops immediately and shows a safe reason | | |
| 429 backs off using `Retry-After` | | |
| Organization header / tenant / business selection correct | | |
| Provider without PO support returns a typed unsupported error | | |
| Excluded resources never called (Sage) | | |
| Tokens stored encrypted; no secret in logs | | |

## Currency results

Record one row per currency actually attempted. Do not infer support.

| Currency | Result (supported / rate required / rejected) | Provider message (safe form) | Human rate recorded? |
|---|---|---|---|
| GBP | | | |
| USD | | | |
| NGN | | | |

## Duplicate and retry result

- First POST response and provider record ID:
- Simulated timeout response:
- Reconciliation query result:
- Retry result and final provider record ID:
- Proof that only one record exists:

## Excluded-resource check (Sage)

- Request log reviewed from: to:
- Banking / payments / receipts calls: none
- Journals / opening balances calls: none
- Sales / products / services / reporting calls: none

## Sign-off

- [ ] Evidence reviewed by engineering
- [ ] No credentials, tokens, or full provider payloads are included
- [ ] Results linked from the ticket log

> Sage has no sandbox. Never label a Sage environment "sandbox". Use the
> registered app against a Sage UK trial business on API 3.1 (Standard or
> Plus for supplier purchase transactions).

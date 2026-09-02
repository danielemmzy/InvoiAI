# QuickBooks → InvoiAI Chart of Accounts

## The simple idea

A Chart of Accounts is just a company's list of accounting categories.

Examples:

- Software
- Advertising
- Rent
- Utilities
- Office Supplies
- Materials

A GL account is one item in that list.

InvoiAI should **not invent GL accounts**. It should select an existing account from the organization's Chart of Accounts.

## Recommended customer flow

```text
Connect QuickBooks
       ↓
InvoiAI reads QuickBooks Account records
       ↓
Store them in chart_of_accounts
       ↓
Cache active accounts in Redis for 60 seconds
       ↓
AI / coding rules choose from those existing accounts
       ↓
Approved invoice uses the QuickBooks Account Id when creating the Bill
```

The customer does not need to manually type hundreds of accounts.

## Sync endpoint

`POST /api/v2/ap/chart-of-accounts/sync`

Requirements:

- active QuickBooks connection
- QuickBooks `realm_id`
- `MANAGE_FINANCE` permission

The endpoint is idempotent. QuickBooks Account `Id` is stored as `chart_of_accounts.external_id`.

## What gets synchronized

For each QuickBooks Account:

- `Id` → `external_id`
- `AcctNum` → `account_code` (falls back to QuickBooks Id when blank)
- `Name` → `account_name`
- `AccountType` → `account_type`
- `AccountSubType` → `account_subtype`
- `Active` → `is_active`
- `SubAccount` → `is_postable`
- `ParentRef.value` → `external_parent_id`
- source → `quickbooks`

Parent relationships are resolved in one SQL statement.

## Why stale accounts are not deleted

Accounting history must remain stable.

If QuickBooks deactivates an account, InvoiAI marks the local account inactive instead of deleting it. Existing invoice coding can therefore continue to reference the historical account.

## Performance

- QuickBooks requests are paginated at 1,000 accounts.
- PostgreSQL is authoritative.
- Redis caches the active organization's account list for 60 seconds.
- Cache failures fall back to PostgreSQL and do not stop accounting operations.
- The normal hourly QuickBooks synchronization also refreshes accounts.

## AI safety rule

The AI can say:

> "This invoice looks like Software."

It then selects an existing active Software account.

It must **not** create a new GL account merely because a vendor or description is unfamiliar.

## No QuickBooks connection

Organizations without QuickBooks can still manually create accounts through:

`POST /api/v2/ap/chart-of-accounts`

But QuickBooks-connected organizations should use synchronization as the primary source.

## QuickBooks Bill creation

When InvoiAI creates a QuickBooks Bill, the local account UUID is **not** sent to QuickBooks.

Instead:

```text
invoice_codings.gl_account_id
        ↓
chart_of_accounts.external_id
        ↓
QuickBooks AccountRef.value
```

That external ID is the QuickBooks Account Id.


Industry-standard notes: COA is internally persisted for tenant-safe, fast coding and external ID mapping; this is not a customer setup task. Redis is an optimization only. Manual sync is rate limited and distributed-lock protected; a six-hour scheduled refresh keeps active QuickBooks accounts current. Personal-mode organizations are excluded from AP matching/coding.

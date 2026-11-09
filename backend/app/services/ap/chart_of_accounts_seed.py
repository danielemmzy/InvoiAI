"""Starter chart of accounts for new/empty organizations.

AP coding needs a destination account for every invoice line. A brand-new
organization has no chart of accounts, so coding can only ever return
"needs review". This module provides a small, standard chart that an
organization can load once and then edit.

Seeding is additive and idempotent: accounts that already exist (matched by
code) are left untouched, including manually renamed or deactivated rows.
"""

from __future__ import annotations

from uuid import UUID

# A deliberately small, standard small-business chart. Codes follow the usual
# US convention: 1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx revenue,
# 5xxx COGS, 6xxx/7xxx expenses. `is_postable=False` would mark header rows;
# this starter only contains postable accounts so AP coding has real targets.
STARTER_ACCOUNTS: list[dict] = [
    {"account_code": "1000", "account_name": "Cash", "account_type": "asset", "account_subtype": "current_asset"},
    {"account_code": "1100", "account_name": "Accounts Receivable", "account_type": "asset", "account_subtype": "current_asset"},
    {"account_code": "1200", "account_name": "Inventory", "account_type": "asset", "account_subtype": "current_asset"},
    {"account_code": "1500", "account_name": "Fixed Assets", "account_type": "asset", "account_subtype": "fixed_asset"},
    {"account_code": "2000", "account_name": "Accounts Payable", "account_type": "liability", "account_subtype": "current_liability"},
    {"account_code": "2100", "account_name": "Sales Tax Payable", "account_type": "liability", "account_subtype": "current_liability"},
    {"account_code": "2200", "account_name": "Credit Cards Payable", "account_type": "liability", "account_subtype": "current_liability"},
    {"account_code": "3000", "account_name": "Owner's Equity", "account_type": "equity", "account_subtype": None},
    {"account_code": "4000", "account_name": "Sales Revenue", "account_type": "revenue", "account_subtype": "operating_revenue"},
    {"account_code": "4100", "account_name": "Service Revenue", "account_type": "revenue", "account_subtype": "operating_revenue"},
    {"account_code": "5000", "account_name": "Cost of Goods Sold", "account_type": "expense", "account_subtype": "cost_of_goods_sold"},
    {"account_code": "6000", "account_name": "Advertising & Marketing", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6100", "account_name": "Software & Subscriptions", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6200", "account_name": "Office Supplies", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6300", "account_name": "Rent & Lease", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6400", "account_name": "Utilities", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6500", "account_name": "Travel", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6600", "account_name": "Meals & Entertainment", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6700", "account_name": "Professional Fees", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6800", "account_name": "Insurance", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "6900", "account_name": "Bank & Card Fees", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "7000", "account_name": "Payroll & Wages", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "7100", "account_name": "Contractor Services", "account_type": "expense", "account_subtype": "operating_expense"},
    {"account_code": "7200", "account_name": "Shipping & Delivery", "account_type": "expense", "account_subtype": "operating_expense"},
]


def missing_starter_accounts(existing_codes: set[str]) -> list[dict]:
    """Return starter rows whose code is not already present."""
    return [account for account in STARTER_ACCOUNTS if account["account_code"] not in existing_codes]


async def seed_starter_chart_of_accounts(org_id: UUID, db=None) -> dict:
    """Insert the starter chart for an organization, skipping existing codes.

    `db` is injectable so the behavior can be tested without Supabase.
    """
    if db is None:
        from app.core.supabase import get_supabase

        db = get_supabase()

    rows = (
        db.table("chart_of_accounts")
        .select("account_code")
        .eq("org_id", str(org_id))
        .execute()
        .data
        or []
    )
    existing_codes = {str(row.get("account_code")) for row in rows}
    missing = missing_starter_accounts(existing_codes)

    if missing:
        payload = [
            {
                **account,
                "org_id": str(org_id),
                "is_active": True,
                "is_postable": True,
                "source": "starter",
            }
            for account in missing
        ]
        db.table("chart_of_accounts").insert(payload).execute()

    return {"created": len(missing), "skipped": len(STARTER_ACCOUNTS) - len(missing)}

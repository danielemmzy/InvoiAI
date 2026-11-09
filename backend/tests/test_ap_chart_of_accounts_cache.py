"""Chart-of-accounts cache scope.

The settings screen can request active-only or active+inactive rows. Those are
different result sets, so they must never share a Redis key.
"""

from uuid import UUID

from app.services.ap.chart_of_accounts_service import ChartOfAccountsService

ORG = UUID("00000000-0000-0000-0000-000000000001")


def test_cache_key_separates_active_and_all_scopes():
    active = ChartOfAccountsService._key(ORG, active_only=True)
    all_rows = ChartOfAccountsService._key(ORG, active_only=False)

    assert active != all_rows
    assert ChartOfAccountsService._cache_keys(ORG) == (active, all_rows)


def test_cache_keys_are_org_scoped():
    other = UUID("00000000-0000-0000-0000-000000000002")

    assert set(ChartOfAccountsService._cache_keys(ORG)).isdisjoint(
        ChartOfAccountsService._cache_keys(other)
    )

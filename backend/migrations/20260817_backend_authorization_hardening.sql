-- Backend-only authorization hardening
-- The frontend does not query these tables directly. FastAPI is the
-- persistence boundary and uses the trusted Supabase service-role client.
-- Keep RLS enabled as defense in depth, but remove PostgREST privileges from
-- anon/authenticated so accidental direct client access fails closed.

REVOKE ALL ON TABLE
    public.allocation_plans,
    public.budget_categories,
    public.debts,
    public.expenses,
    public.goals,
    public.income_entries,
    public.insights,
    public.recurring_items,
    public.payment_allocations,
    public.notification_deliveries,
    public.stripe_events
FROM anon, authenticated;

-- RLS remains enabled. We intentionally do not FORCE RLS because the backend
-- service-role connection is the trusted persistence boundary.

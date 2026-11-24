-- Batched, atomic coding-rule match counters.
--
-- GL coding used to call increment_coding_rule_match once per matched line.
-- This function applies every count for one document in a single statement,
-- with the increment still performed inside the database so concurrent coding
-- runs cannot lose updates.
--
-- Additive and idempotent. Safe to run more than once.
-- NOT APPLIED: the backend falls back to the existing single-rule RPC until
-- this migration is reviewed and run.

create or replace function public.increment_coding_rule_matches(p_counts jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.coding_rules as rules
    set match_count = coalesce(rules.match_count, 0) + deltas.total,
        updated_at = now()
    from (
        select
            (entry ->> 'rule_id')::uuid as rule_id,
            sum((entry ->> 'count')::int) as total
        from jsonb_array_elements(coalesce(p_counts, '[]'::jsonb)) as entry
       -- Ignores a caller that repeats the same rule id in one payload.
        group by 1
    ) as deltas
    where rules.id = deltas.rule_id;
end;
$$;

-- The function runs as its owner, so it must not be callable by end users:
-- the backend (service role) calls it with rule ids that were already read
-- through an org-scoped query. Granting it to `authenticated` would let a
-- signed-in user from another organization write to these counters.
revoke all on function public.increment_coding_rule_matches(jsonb) from public;
revoke all on function public.increment_coding_rule_matches(jsonb) from authenticated, anon;
grant execute on function public.increment_coding_rule_matches(jsonb) to service_role;

commit;
notify pgrst, 'reload schema';

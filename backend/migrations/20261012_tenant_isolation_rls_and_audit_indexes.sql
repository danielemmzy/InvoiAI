-- Ticket 4: tenant isolation, RLS, and audit indexes.
-- Additive and idempotent. Applied after the canonical migration chain.
--
-- Policy shape: an authenticated member may touch a row only when they have
-- an active membership in the row's organization. The service role used by
-- workers bypasses RLS by design; workers must derive the organization from
-- the record they were asked to process, never from a job payload.
--
-- Tables created before the migration manifest may not exist in every
-- environment, so every statement is guarded by to_regclass().

-- ---------------------------------------------------------------------------
-- 1. Tenant-owned tables with a direct org_id column
-- ---------------------------------------------------------------------------

do $$
declare
    table_name text;
    tables text[] := array[
        'documents',
        'document_line_items',
        'invoice_codings',
        'invoice_exceptions',
        'invoice_comments',
        'vendors',
        'chart_of_accounts',
        'purchase_orders',
        'goods_receipts',
        'approval_workflows',
        'approval_steps',
        'approval_history',
        'approval_authorities',
        'approval_delegations',
        'sod_rules',
        'audit_logs',
        'integration_connections',
        'integration_syncs',
        'integration_webhooks',
        'ap_email_intake_events',
        'ap_email_intake_attachments',
        'vendor_credits',
        'vendor_credit_applications',
        'vendor_credit_events',
        'payment_instructions',
        'payment_instruction_events',
        'payment_authorizations',
        'payment_allocations',
        'payments',
        'vendor_document_requests',
        'accounting_tax_code_mappings',
        'ap_approval_groups',
        'ap_approval_group_members',
        'coding_rules',
        'allocation_plans',
        'organization_settings',
        'organization_usage',
        'notifications',
        'notification_deliveries'
    ];
    policy_name text;
begin
    foreach table_name in array tables loop
        if to_regclass('public.' || table_name) is null then
            continue;
        end if;

        if not exists (
            select 1
            from information_schema.columns
            where table_schema = 'public'
              and table_name = table_name
              and column_name = 'org_id'
        ) then
            raise notice 'Skipping RLS for %.%: no org_id column', 'public', table_name;
            continue;
        end if;

        execute format('alter table public.%I enable row level security', table_name);

        policy_name := table_name || '_org_member';
        if not exists (
            select 1
            from pg_policies
            where schemaname = 'public'
              and tablename = table_name
              and policyname = policy_name
        ) then
            execute format(
                'create policy %I on public.%I for all to authenticated '
                'using (exists (select 1 from public.org_members m '
                'where m.org_id = %I.org_id and m.user_id = auth.uid() and m.is_active = true)) '
                'with check (exists (select 1 from public.org_members m '
                'where m.org_id = %I.org_id and m.user_id = auth.uid() and m.is_active = true))',
                policy_name, table_name, table_name, table_name
            );
        end if;
    end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 2. Child rows without org_id: authorize through the parent row
-- ---------------------------------------------------------------------------

do $$
begin
    if to_regclass('public.goods_receipt_lines') is not null
       and to_regclass('public.goods_receipts') is not null then
        execute 'alter table public.goods_receipt_lines enable row level security';

        if not exists (
            select 1 from pg_policies
            where schemaname = 'public'
              and tablename = 'goods_receipt_lines'
              and policyname = 'goods_receipt_lines_org_member'
        ) then
            execute '
                create policy goods_receipt_lines_org_member
                on public.goods_receipt_lines for all to authenticated
                using (exists (
                    select 1 from public.goods_receipts r
                    join public.org_members m on m.org_id = r.org_id
                    where r.id = goods_receipt_lines.goods_receipt_id
                      and m.user_id = auth.uid()
                      and m.is_active = true
                ))
                with check (exists (
                    select 1 from public.goods_receipts r
                    join public.org_members m on m.org_id = r.org_id
                    where r.id = goods_receipt_lines.goods_receipt_id
                      and m.user_id = auth.uid()
                      and m.is_active = true
                ))';
        end if;
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Audit indexes: organization, actor, resource, event, time
-- ---------------------------------------------------------------------------

do $$
begin
    if to_regclass('public.audit_logs') is not null then
        execute 'create index if not exists idx_audit_logs_org_created
                 on public.audit_logs(org_id, created_at desc)';
        execute 'create index if not exists idx_audit_logs_org_actor_created
                 on public.audit_logs(org_id, user_id, created_at desc)';
        execute 'create index if not exists idx_audit_logs_org_resource_created
                 on public.audit_logs(org_id, resource_type, resource_id, created_at desc)';
        execute 'create index if not exists idx_audit_logs_org_action_created
                 on public.audit_logs(org_id, action, created_at desc)';
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- 4. Fast tenant lookups for the AP workflow
-- ---------------------------------------------------------------------------

do $$
begin
    if to_regclass('public.documents') is not null then
        execute 'create index if not exists idx_documents_org_status_updated
                 on public.documents(org_id, ap_status, updated_at desc)';
        execute 'create index if not exists idx_documents_org_erp_bill
                 on public.documents(org_id, erp_bill_id)';
    end if;

    if to_regclass('public.invoice_exceptions') is not null then
        execute 'create index if not exists idx_invoice_exceptions_org_status
                 on public.invoice_exceptions(org_id, status, created_at desc)';
    end if;

    if to_regclass('public.invoice_codings') is not null then
        execute 'create index if not exists idx_invoice_codings_org_document
                 on public.invoice_codings(org_id, document_id)';
    end if;

    if to_regclass('public.payment_instructions') is not null then
        execute 'create index if not exists idx_payment_instructions_org_status
                 on public.payment_instructions(org_id, status, created_at desc)';
    end if;
end $$;

comment on table public.documents is
    'Tenant-owned AP documents. RLS limits authenticated access to active org members; service-role workers derive org_id from the record.';

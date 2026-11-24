# Document Hub — Architecture Proposal

> **Status:** proposal for approval. No code, schema or dependency has been changed.
> Design constraints come from `DISCOVERY.md` §2 (interview answers) and `PRODUCTION_ROADMAP.md`
> (AP-only launch scope, tenant isolation, no posting, no e-invoicing claims).

## 1. One-sentence architecture

A **renderer plus registry**: adapters read existing AP records into an immutable snapshot, a sandboxed
Jinja2 template renders that snapshot to HTML, WeasyPrint produces PDF bytes, and a registry table owns
the document's identity, number, lifecycle and frozen artifact — while the financial records keep all
authority.

## 2. Why not extend the existing `documents` table

`documents` is the **inbox** (`backend/app/models/domain/document.py`): intake, OCR stage,
`DocumentStatus` values such as `ocr_running` and `needs_review`, archive flags. Outbound documents need
a different lifecycle (`draft → approved → issued → voided/superseded`), a number series, template
versions and frozen bytes. Putting both in one table would force every existing intake query to filter
by a new discriminator and would let two lifecycles overwrite one `status` column.

Decision: **separate registry table**, with an optional nullable link from the source record back to the
issued document (see §7, question 3 in `DISCOVERY.md`).

## 3. Layer responsibilities

| Layer | Module (proposed) | Does | Must not |
|---|---|---|---|
| Source adapters | `app/services/hub/sources/` | Read PO / goods receipt / payment instruction / bill / expense / report query into a typed snapshot DTO | Write to source tables, recompute amounts differently from the owning module |
| Snapshot freeze | `app/services/hub/snapshots.py` | Serialise DTO + source id + source updated_at + generated_at into `render_context` jsonb; compute `source_hash` | Mutate an existing snapshot in place |
| Templates | `app/services/hub/templates.py` | Load a versioned template, sanitise HTML/CSS, render with `jinja2.sandbox.SandboxedEnvironment` and allowlisted filters | Execute arbitrary Python, touch the DB, call the network, or emit fetching/attachment markup (§9.1) |
| Render | `app/services/hub/render.py` | HTML → PDF via WeasyPrint with a deny-all `url_fetcher` and output assertions; reports → XLSX (openpyxl) / CSV | Read the database directly, resolve URLs, or receive a caller-supplied path |
| Registry | `app/services/hub/registry.py` + `app/repositories/hub/` | Create draft, approve, assign number, issue, void, supersede; store bytes via existing `StorageService`; emit events | Change source records, post anything, delete issued artifacts |
| Numbering | `app/services/hub/numbering.py` + SQL function | Atomic per-org, per-kind series (`PO-000001`) | Reuse or recycle numbers |
| API | `app/routers/document_hub.py` | Auth, org scoping, permissions, rate limits, signed URLs | Contain layout logic |

Existing services are reused rather than duplicated: `StorageService` (`app/services/storage/storage.py`),
`ExportService`/exporters (`app/services/export/`), `require_permission` / `require_fresh_mfa` /
`slowapi` limiters, `get_org_context`, `PlatformError`.

## 4. Data model (proposed, not applied)

Follows `backend/migrations/20261012_tenant_isolation_rls_and_audit_indexes.sql`: `org_id` on every
tenant table, RLS enabled, audit indexes, additive and idempotent SQL.

### 4.1 `document_templates`

```sql
create table if not exists public.document_templates (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    doc_kind text not null,              -- 'purchase_order' | 'goods_receipt' | 'remittance_advice'
                                         -- | 'vendor_bill_cover' | 'ap_summary' | 'expense_report'
                                         -- | 'letter'
    name text not null,
    version int not null default 1,
    body_html text not null,             -- Jinja2 source
    stylesheet_css text not null default '',
    is_published boolean not null default false,
    is_system boolean not null default false,   -- built-in layout, org may clone not edit
    created_by uuid references auth.users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (org_id, doc_kind, name, version)
);
```

Published versions are immutable; editing creates `version + 1`. Issued documents reference
`(template_id, template_version)` so a later template change can never alter an old PDF.

### 4.2 `issued_documents`

```sql
create table if not exists public.issued_documents (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    doc_kind text not null,
    template_id uuid references public.document_templates(id),
    template_version int,
    document_number text,                 -- null until issued
    status text not null default 'draft', -- draft|approved|issued|voided|superseded
    source_type text not null,            -- 'purchase_order'|'goods_receipt'|'payment_instruction'
                                          -- |'document'|'expense'|'report_query'|'manual'
    source_id uuid,
    source_updated_at timestamptz,
    render_context jsonb not null,        -- frozen values actually rendered
    source_hash text,                     -- sha256 of the canonical render_context JSON
    idempotency_key text,                 -- caller-supplied, unique per org
    render_engine text,                   -- e.g. 'weasyprint-70.x'; keeps output reproducible
    file_path text,                       -- storage object path, null for XLSX/CSV-only
    file_sha256 text,
    voided_file_path text,                -- separately rendered, watermarked copy (original bytes untouched)
    voided_file_sha256 text,
    file_size_bytes bigint,
    page_count int,
    issued_at timestamptz,
    issued_by uuid,
    approved_at timestamptz,
    approved_by uuid,
    voided_at timestamptz,
    voided_by uuid,
    void_reason text,
    supersedes_id uuid references public.issued_documents(id),
    created_by uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint issued_documents_status_valid
        check (status in ('draft','approved','issued','voided','superseded')),
    constraint issued_number_required
        check (status not in ('issued','voided','superseded') or document_number is not null),
    constraint issued_idempotency_key_sane
        check (idempotency_key is null or length(idempotency_key) between 1 and 200)
);

create unique index if not exists uq_issued_documents_org_number
    on public.issued_documents (org_id, document_number)
    where document_number is not null;

-- Idempotency: a retried issue request resolves to the existing row instead of
-- minting a second number or a second file.
create unique index if not exists uq_issued_documents_org_idempotency
    on public.issued_documents (org_id, idempotency_key)
    where idempotency_key is not null;

create index if not exists ix_issued_documents_org_kind_status
    on public.issued_documents (org_id, doc_kind, status, created_at desc);

create index if not exists ix_issued_documents_source
    on public.issued_documents (org_id, source_type, source_id);

create index if not exists ix_issued_documents_number
    on public.issued_documents (org_id, document_number)
    where document_number is not null;
```

`render_context` is the contract. It is written once and never updated after `approved`; if the source
record changes afterwards, the UI must show "source updated since generation" rather than silently
re-render. Decimal values are serialised as **strings** in the JSON (never floats) so the snapshot cannot
lose precision in a round trip.

**Immutability is enforced in the database, not only in the service layer.** A `before update` trigger
rejects changes to `document_number`, `render_context`, `source_hash`, `file_path`, `file_sha256`,
`template_id`/`template_version` and `issued_*` once the row leaves `draft`/`approved`, and rejects any
transition out of `voided` or `superseded`. Only lifecycle fields (`status`, `void_reason`, `voided_*`,
`supersedes_id`) may change. Application code that forgets the rule gets an error, not a corrupted
record.

```sql
create or replace function public.guard_issued_document_immutability()
returns trigger language plpgsql as $$
begin
    if old.status in ('issued','voided','superseded') then
        if new.document_number  is distinct from old.document_number
        or new.render_context   is distinct from old.render_context
        or new.source_hash      is distinct from old.source_hash
        or new.file_path        is distinct from old.file_path
        or new.file_sha256      is distinct from old.file_sha256
        or new.template_id      is distinct from old.template_id
        or new.template_version is distinct from old.template_version
        or new.issued_at        is distinct from old.issued_at
        or new.source_id        is distinct from old.source_id then
            raise exception 'ISSUED_DOCUMENT_IMMUTABLE' using errcode = 'P0001';
        end if;
    end if;
    if old.status = 'voided' and new.status <> 'voided' then
        raise exception 'VOID_IS_TERMINAL' using errcode = 'P0001';
    end if;
    if old.status = 'superseded' and new.status <> 'superseded' then
        raise exception 'SUPERSEDED_IS_TERMINAL' using errcode = 'P0001';
    end if;
    if old.status = 'approved' and new.status = 'approved'
       and new.render_context is distinct from old.render_context then
        raise exception 'APPROVED_CONTEXT_FROZEN' using errcode = 'P0001';
    end if;
    return new;
end $$;

drop trigger if exists trg_issued_documents_immutable on public.issued_documents;
create trigger trg_issued_documents_immutable
    before update on public.issued_documents
    for each row execute function public.guard_issued_document_immutability();
```

Deletion: `authenticated` is granted no `DELETE` on this table, and there is no RLS delete policy. Only
the organization cascade (account deletion) or an explicitly audited service-role purge may remove rows;
a purge sets `app.allow_document_purge = 'on'` for the transaction so the guard is bypassable on purpose,
not by accident.

### 4.3 `issued_document_events`

```sql
create table if not exists public.issued_document_events (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    issued_document_id uuid not null references public.issued_documents(id) on delete cascade,
    event_type text not null,   -- created|approved|issued|downloaded|voided|superseded|regenerated
    actor_id uuid,
    data jsonb not null default '{}'::jsonb,   -- includes document_number and file_sha256 on 'issued'
    created_at timestamptz not null default now(),
    constraint issued_document_events_type_valid check (event_type in (
        'created','approved','issued','downloaded','voided','superseded','regenerated'
    ))
);

create index if not exists ix_issued_document_events_doc_time
    on public.issued_document_events (org_id, issued_document_id, created_at);
```

**Resolved in Phase 0 (no longer an assumption):** `AuditService` is a generic sink. Its
`log(org_id, user_id, action, resource_type, resource_id, old_values, new_values, ...)` signature fits
issuance events, and `audit_logs` already has the org/actor/resource/time indexes from
`20261012_tenant_isolation_rls_and_audit_indexes.sql`. Decision: write the **compliance trail** through
`AuditService.log` (action names such as `document.issued`, `document.voided`) and keep
`issued_document_events` as the **document timeline** rendered in the UI, both from one helper so they
cannot diverge. `issued_document_events` gets no update/delete policy; `AuditService` already documents
"always write, never update or delete".

### 4.4 Number series (generalising the PO implementation)

```sql
create table if not exists public.document_number_series (
    org_id uuid not null references public.organizations(id) on delete cascade,
    doc_kind text not null,
    prefix text not null,
    last_number bigint not null default 0 check (last_number >= 0),
    updated_at timestamptz not null default now(),
    primary key (org_id, doc_kind),
    constraint document_number_series_prefix_format check (prefix ~ '^[A-Z]{2,4}$'),
    -- One prefix per organization: two kinds sharing a prefix would collide on
    -- (org_id, document_number) in issued_documents and fail at issue time.
    unique (org_id, prefix)
);

create or replace function public.next_document_number(
    p_org_id uuid, p_doc_kind text, p_prefix text
)
returns text language plpgsql security definer set search_path = public as $$
declare v_prefix text; v_next bigint;
begin
    if p_org_id is null then raise exception 'ORG_ID_REQUIRED' using errcode = 'P0001'; end if;
    if p_doc_kind is null or p_doc_kind !~ '^[a-z][a-z0-9_]{2,39}$' then
        raise exception 'DOC_KIND_INVALID' using errcode = 'P0001';
    end if;
    if p_prefix is null or p_prefix !~ '^[A-Z]{2,4}$' then
        raise exception 'DOC_PREFIX_INVALID' using errcode = 'P0001';
    end if;

    -- Atomic: concurrent issues serialize on the primary key instead of receiving
    -- the same number. The existing row's prefix wins on conflict, so a later
    -- caller cannot rename a series that has already issued documents.
    insert into public.document_number_series (org_id, doc_kind, prefix, last_number)
    values (p_org_id, p_doc_kind, p_prefix, 1)
    on conflict (org_id, doc_kind) do update
        set last_number = public.document_number_series.last_number + 1,
            updated_at = now()
    returning prefix, last_number into v_prefix, v_next;

    return v_prefix || '-' || lpad(v_next::text, 6, '0');
end; $$;

-- Same access shape as the existing PO generator: no direct client execution.
revoke all on function public.next_document_number(uuid, text, text) from public, anon, authenticated;
grant execute on function public.next_document_number(uuid, text, text) to service_role;
```

Prefixes are an explicit map owned by the service layer, not derived from the kind name:
`purchase_order→PO`, `goods_receipt→GR`, `remittance_advice→REM`, `vendor_bill_cover→COV`,
`ap_summary→SUM`, `ap_ageing_report→AGE`, `spend_report→SPD`, `expense_report→EXP`, `letter→DOC`.
*(An earlier draft derived the prefix with `upper(left(doc_kind, 2))`, which yields `PU` for
`purchase_order` and the same `AP` prefix for two different report kinds — the `unique (org_id, prefix)`
constraint now makes that a loud failure instead of a duplicate number.)*

How the numbering guarantees are met:

- **Atomic** — single `insert … on conflict do update` on the `(org_id, doc_kind)` primary key; concurrent
  callers serialize in the database.
- **Unique** — `unique (org_id, prefix)` on the series, `unique (org_id, document_number)` on issued rows,
  and numbers are only assigned inside the issue transaction.
- **Never reused** — the counter is monotonic, never decremented, never reset; there is no code path that
  reads `min` or `count`, and issued rows cannot be deleted through the application.
- **Gaps permitted** — a transaction that rolls back after allocation leaves a hole. This is expected and
  allowed (matching the existing PO implementation); a gap has no row and no event, by definition.
- **Auditable** — the `issued` event carries the number and the file hash; the series row keeps
  `last_number` and `updated_at`; the issued row keeps `issued_at`/`issued_by`; the compliance copy goes
  to `audit_logs` via `AuditService`. Four independent records agree, so a number cannot be produced
  or altered without a trace.
- **Assigned at issue, not at draft** — abandoned drafts consume no number; a voided document keeps its
  number forever.

`purchase_orders.org_number` stays as it is. The hub does not take over PO numbering; if a PO has no
`org_number`, the hub renders `po_number` and says so.

### 4.5 Company profile addition

Add a small, additive profile surface (new columns on `organizations`, or `organization_document_profile`
if the org table is at its comfort limit):

`legal_name`, `address_line1`, `address_line2`, `city`, `region`, `postal_code`, `address_country`,
`registration_number`, `document_phone`, `document_email`, `document_footer`.

`name`, `tax_id`, `logo_url`, `country`, `currency`, `brand_color` already exist on `Organization` /
`OrganizationSettings` and are reused. **No bank details** — `Vendor.bank_account_hash` shows the
codebase deliberately avoids storing plaintext account numbers, and Q4 excluded it.

### 4.6 Model review: isolation, RLS, indexes, idempotency, auditability, consistency

Reviewed against `20261012_tenant_isolation_rls_and_audit_indexes.sql` and the existing AP tables.

**Row-level security.** The 20261012 migration enables RLS and creates `{table}_org_member` policies for
`for all to authenticated`. That is *not* sufficient for this feature: these tables need append-only
behaviour, so the policies are split deliberately instead of copied verbatim.

```sql
alter table public.document_templates     enable row level security;
alter table public.issued_documents       enable row level security;
alter table public.issued_document_events enable row level security;
alter table public.document_number_series enable row level security;

-- templates: members may read/create/update their org's rows; no delete
create policy document_templates_org_read on public.document_templates
    for select to authenticated using (public.is_org_member(org_id));
create policy document_templates_org_write on public.document_templates
    for insert to authenticated with check (public.is_org_member(org_id));
create policy document_templates_org_update on public.document_templates
    for update to authenticated using (public.is_org_member(org_id))
    with check (public.is_org_member(org_id));

-- issued documents: read/create/update lifecycle; NO delete policy
create policy issued_documents_org_read on public.issued_documents
    for select to authenticated using (public.is_org_member(org_id));
create policy issued_documents_org_insert on public.issued_documents
    for insert to authenticated with check (public.is_org_member(org_id));
create policy issued_documents_org_update on public.issued_documents
    for update to authenticated using (public.is_org_member(org_id))
    with check (public.is_org_member(org_id));

-- events: append and read only
create policy issued_document_events_org_read on public.issued_document_events
    for select to authenticated using (public.is_org_member(org_id));
create policy issued_document_events_org_append on public.issued_document_events
    for insert to authenticated with check (public.is_org_member(org_id));

-- series: readable, never writable by clients (writes go through the definer function)
create policy document_number_series_org_read on public.document_number_series
    for select to authenticated using (public.is_org_member(org_id));
```

`is_org_member(uuid)` is a small `stable security definer` helper wrapping the same
`org_members … is_active = true` predicate the existing policies inline. It is introduced here as a
proposal: if the helper already exists under another name, use that instead of adding a second one.

**Findings and resolutions**

| # | Area | Finding | Resolution |
|---|---|---|---|
| 1 | Numbering | An earlier draft derived prefixes with `upper(left(doc_kind,2))` → `PU`, and gave two report kinds the same `AP` prefix, which would violate `unique (org_id, document_number)` at issue time | Explicit prefix map; `unique (org_id, prefix)`; format check |
| 2 | Numbering | The proposed function had no `revoke`/`grant`, unlike the PO generator | Copied the existing pattern: no `authenticated` execute, `service_role` only |
| 3 | Idempotency | Prose mentioned an idempotency key but the DDL had no column | `idempotency_key` + unique partial index `(org_id, idempotency_key)` |
| 4 | Immutability | Nothing stopped an update to an issued row | `guard_issued_document_immutability` trigger; terminal states enforced |
| 5 | Deletion | No rule said whether issued rows may be deleted | No delete policy, no `DELETE` grant; audited purge only |
| 6 | Audit | Risk of two competing histories (`audit_logs` vs events) | `AuditService` verified generic; write both from one helper with defined roles |
| 7 | Indexes | Events had no index; number lookups relied on the unique index only | Added `(org_id, issued_document_id, created_at)` and a partial number index |
| 8 | Status | `status` was free text | `check (status in ('draft','approved','issued','voided','superseded'))` |
| 9 | Template integrity | `(template_id, template_version)` is not a composite FK | `template_id` points at the immutable version row; `template_version` is a display copy; the trigger freezes both |
| 10 | Precision | `jsonb` round-trips can turn decimals into floats | Serialise money as strings in `render_context`; never `float()` in the render path |
| 11 | Consistency | `org_id … on delete cascade` matches `purchase_order_number_counters`; `actor_id`/`created_by` are plain `uuid`, matching `payment_instruction_events.actor_id` (only onboarding tables use an `auth.users` FK) | Kept consistent; confirm on staging in Phase 0 |
| 12 | Consistency | The inbound `documents` table is untouched; no discriminator added | By design (DH-007) |

**Still open (recorded, not invented)**

- **System templates.** `document_templates.org_id` is `not null`, so a "built-in" template must either be
  seeded per organization at creation or allowed to be global (`org_id is null` with a separate read
  policy). Both are defensible; the choice changes the RLS statement and the seeding migration.
- **Source record deletion.** `source_type`/`source_id` is polymorphic (no FK by design). If a PO or bill is
  hard-deleted, the issued document must not disappear with it: keep the snapshot and mark it orphaned, or
  refuse the source delete. Not decided.
- **Permission mapping.** The two new permission strings need a role mapping decision (which existing roles
  receive `documents:issue`), which is a product question, not an engineering one.

## 5. Render context contract (the important part)

```python
@dataclass(frozen=True, slots=True)
class DocumentHeader:
    title: str                  # "Purchase Order"
    document_number: str | None # internal ref, may be "PO (unassigned)" pre-issue
    source_reference: str | None# provider po_number / receipt external_id
    issue_date: date | None
    currency: str
    status_label: str           # Draft / Approved / Issued / Voided

@dataclass(frozen=True, slots=True)
class PartyBlock:
    role: str                   # "Buyer" | "Supplier" | "Payee"
    name: str
    address_lines: list[str]
    tax_id: str | None
    registration_number: str | None
    contact: str | None

@dataclass(frozen=True, slots=True)
class DocumentLine:
    position: int
    description: str
    sku: str | None
    quantity: Decimal | None
    unit_of_measure: str | None
    unit_price: Decimal | None
    amount: Decimal | None
    note: str | None

@dataclass(frozen=True, slots=True)
class DocumentTotals:
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    currency: str
    # provenance only — never recomputed across modules
    source_module: str          # "purchase_orders" / "payment_instructions" / ...
    source_id: UUID
    source_updated_at: datetime
    snapshot_taken_at: datetime

@dataclass(frozen=True, slots=True)
class RenderContext:
    branding: BrandingBlock
    header: DocumentHeader
    parties: list[PartyBlock]
    lines: list[DocumentLine]
    totals: DocumentTotals | None
    notes: list[str]
    footer: str | None
    watermark: str | None      # "DRAFT" | "VOID" | None
```

Rules encoded in the contract:

- `Decimal` everywhere for money; formatting is a template filter, never float arithmetic.
- Totals are **carried**, not recomputed. Where the source module already stores
  `subtotal`/`tax_amount`/`total_amount` (the `documents` table does), the adapter copies them. If a
  source has only a single amount (e.g. `PurchaseOrder.amount`), the context carries that amount and no
  invented breakdown.
- Every context includes `source_module`, `source_id`, `source_updated_at`, `snapshot_taken_at`, and the
  rendered document prints the generation timestamp — satisfying Q3's traceability requirement.
- `watermark` makes draft/issued/void visually unmistakable.

## 6. Document kinds in V1

| `doc_kind` | Source | Number series | Notes |
|---|---|---|---|
| `purchase_order` | `purchase_orders` + lines (`metadata.line_items` or line table) | none (uses existing `org_number`/`po_number`) | Never edits the PO |
| `goods_receipt` | `goods_receipts` + `goods_receipt_lines` | none (uses `receipt_number`) | Shows accepted/rejected quantities as recorded |
| `remittance_advice` | `payment_instructions` (+ `vendors`, related bills) | `REM-000001` | Closes the roadmap's missing "printable PDF" half |
| `vendor_bill_cover` | `documents` + `InvoiceCoding` | `COV-000001` | Cover sheet + coding summary, amounts copied from the bill |
| `ap_summary` | read-only aggregate query | `SUM-000001` | Operational summary of records held in InvoiAI, not a financial statement |
| `ap_ageing_report` | `documents` with `due_date` + recorded allocations | `AGE-000001` | XLSX/CSV primary, PDF optional; only rows with a recorded due date |
| `spend_report` | `documents` + `invoice_codings` | `SPD-000001` | Same; uncoded bills appear as `Uncoded`, never reassigned |
| `expense_report` | `Expense` — **user/owner-scoped, has no `org_id`** | `EXP-000001` | Cannot be an org-wide report from the current model; see §6.1 and open decision 6 |
| `letter` | manual header fields + free body | `DOC-000001` | Internal letterhead only; no contractual language |

Out of scope by answer: sales invoices, credit notes to customers, statutory/tax documents, contracts,
HR records, e-invoicing.

### 6.1 Report data contract (binding on implementation)

InvoiAI holds AP **operational records** — bills, codings, purchase orders, goods receipts, payment
instructions and payments. It does not hold a general ledger, journals, accruals, a period close, bank
reconciliation, budgets or FX revaluation. Reports must be built so they cannot be mistaken for any of
those.

**Rules**

1. Every report declares, in code and on the output: source tables, required fields, filter parameters,
   `as_of` timestamp, and the population included.
2. **Coverage block on every report** (PDF footer and XLSX/CSV header rows): records considered, records
   included, records excluded with counts per reason (`missing_due_date`, `missing_amount`, `uncoded`,
   `no_recorded_allocation`). Excluded records are never treated as zero.
3. Only recorded values are copied. The single derived value permitted is an ageing bucket, computed from
   `documents.due_date` against `as_of`, and it must be labelled as computed from the recorded due date.
   `balance_due` is used exactly as recorded; if null it is shown as `—`, never estimated.
4. Totals are sums of included rows within one currency, printed per currency. **No cross-currency total**
   and no conversion — `OrganizationSettings.default_currency` is not a licence to add currencies
   together.
5. A report is generated for a fixed, recorded set of filters; changing filters creates a new document,
   it does not edit an old one.
6. **Forbidden framing.** No document or screen in this feature may be titled, labelled, exported as, or
   described as: ledger, general ledger, trial balance, statement of account, P&L, profit and loss,
   balance sheet, aged debtor/creditor statement, or statutory report. The only permitted framing is
   "AP working report derived from records in InvoiAI".
7. A standing disclaimer is printed, not tooltipped: *"Derived from bills, purchase orders, goods
   receipts and payment instructions recorded in InvoiAI. Not a statement of account and not a complete
   accounting ledger. Amounts reflect recorded data only."*
8. `payment_status` / payment-instruction `status` are InvoiAI workflow states, not confirmation of funds.
   Any column showing them must carry the workflow wording, not "paid" unless the source says paid.
9. **Expense reports are owner-scoped.** `Expense` carries `owner_type`/`owner_id` and no `org_id`, so an
   org-wide expense report cannot be produced without a schema change. V1 either limits this kind to the
   requester's own records or drops it — an open decision, not something to paper over.

**Acceptance check (Phase 2 gate):** a report generated against a fixture where 40% of bills lack
`due_date` must show `included: 60, excluded: 40 (missing_due_date)` and must not total the excluded 40 as
zero.

## 7. Lifecycle

```
        create ──► draft ──► approved ──► issued ──► voided (terminal)
                     │          │           │
                     │          │           └──► superseded (terminal)
                     │          └── edit resets to draft (approval revoked)
                     └──► discarded (no number consumed, no artifact)
```

### 7.1 States and transitions

| From | To | Conditions | Effect |
|---|---|---|---|
| — | `draft` | Source record readable in the caller's org; template published | Snapshot written; **no number**; no artifact |
| `draft` | `draft` | Explicit refresh | Snapshot re-resolved from live records and replaced; preview only |
| `draft` | `approved` | Validation passes; approver permission; **or issue directly if approval is not required** (open decision 2) | `render_context` frozen, `source_hash` recorded, `approved_at/by` set |
| `approved` | `draft` | Any edit to snapshot-bearing content | Approval revoked, context re-resolvable, `approved_*` cleared |
| `approved` | `issued` | `Idempotency-Key` supplied; template version published | Number assigned atomically **in this transaction**, PDF rendered, uploaded and verified, `file_sha256` + `page_count` recorded |
| `issued` | `voided` | Reason required | Original number and bytes kept; a **separate watermarked copy** is generated and stored (`voided_file_*`), so the frozen original is never re-rendered |
| `issued` | `superseded` | A replacement for the same source is issued | Old row stays readable and downloadable; new row points back via `supersedes_id` |
| `voided` | — | Terminal | Cannot be un-voided or reissued; correct by issuing a replacement |
| `superseded` | — | Terminal | Remains part of the record; not deleted |
| `draft` | deleted | Draft never issued; retention window elapsed or user discards | Row and any preview artifact removed; no number was consumed, so the series is unaffected |

Two deliberate consequences:

- **Voiding never rewrites history.** The issued PDF is not re-rendered; a second artifact carries the
  watermark. Hash comparison proves the original is unchanged.
- **A rejected approval is not a state.** If approval is enabled, rejection returns the document to
  `draft` with a recorded reason in `issued_document_events`; it does not create a `rejected` terminal
  state that would fragment the model. (Whether rejection is editable or discards the draft is open
  decision 2.)

### 7.2 Permission matrix

| Action | Permission | Extra requirement |
|---|---|---|
| List, view, view timeline | `documents:view` | Org membership (RLS + org check → 404 cross-tenant) |
| Create draft, refresh, edit draft | `documents:issue` | Source record must be in the same org |
| Approve / reject | `documents:issue` in V1; a distinct `documents:approve` if segregation of duties is required (open decision 2) | Approver ≠ creator when SoD is enabled |
| Issue | `documents:issue` | `Idempotency-Key` header; rate limited |
| Download (current or voided copy) | `documents:view` | `require_fresh_mfa`; ≤300 s signed URL or streamed response |
| Void | `documents:issue` | `void_reason` required; audited |
| Supersede | `documents:issue` | Replacement draft linked to the old row |
| Manage templates | `documents:templates:manage` | Publish compiles and sanitises before saving |
| Company document profile | `settings:update` | Existing settings permission, not a new one |
| Report render | `documents:view` | `limiter.limit("10/minute")` |

Immutability is enforced by the trigger in §4.2, not by these rules alone: a caller who bypasses the API
still cannot rewrite an issued document. Cross-tenant behaviour copies `export_v2.py` — verify user,
verify org membership, compare `org_id`, return **404** rather than 403 for another tenant's id.

## 8. API surface (proposed)

Prefix `/hub`, router-level `Depends(require_verified_user)`.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/hub/documents` | `documents:view` | List with `kind`, `status`, `q`, date range; URL-backed filters |
| POST | `/hub/documents` | `documents:issue` | Create draft from `{doc_kind, source_type, source_id, template_id}` |
| GET | `/hub/documents/{id}` | `documents:view` | Header, lifecycle, snapshot metadata |
| GET | `/hub/documents/{id}/preview` | `documents:view` | Rendered **PDF streamed from memory** — never HTML served from the app origin (§9.1) |
| GET | `/hub/documents/{id}/download` | `documents:view` + fresh MFA | Streams PDF or returns ≤300 s signed URL |
| PATCH | `/hub/documents/{id}` | `documents:issue` | Edit draft notes/presentation only; 409 if not draft |
| POST | `/hub/documents/{id}/approve` | `documents:issue` | draft → approved |
| POST | `/hub/documents/{id}/issue` | `documents:issue` | approved → issued; `Idempotency-Key` header required, replay returns the existing row |
| POST | `/hub/documents/{id}/void` | `documents:issue` | Reason required |
| POST | `/hub/documents/{id}/supersede` | `documents:issue` | Creates a draft linked to the old one |
| GET/POST | `/hub/templates` | `documents:templates:manage` | List / create new version |
| POST | `/hub/templates/{id}/publish` | `documents:templates:manage` | Compile check then publish |
| GET | `/hub/reports/{report_key}/render` | `documents:view` | `format=pdf|xlsx|csv`, limit 10/minute |

Two new permission strings (`documents:issue`, `documents:templates:manage`) must be added to
`app/core/permissions.py` and mapped to existing roles — reuse `documents:view` for reading. Every
download route keeps the `require_fresh_mfa` + `limiter.limit("10/minute")` pattern already used by
`export_v2.py`.

## 9. Rendering pipeline

```
draft/preview                         issue
source adapters ─► RenderContext ─► Jinja2 (Sandboxed) ─► HTML
                                                          │
                                          WeasyPrint ─────┘─► PDF bytes
                                                               │
                                        pypdfium2: page count, sanity check
                                                               │
                                    StorageService.upload_and_verify ─► registry row + event
```

- **Templates are sandboxed and sanitised.** `jinja2.sandbox.SandboxedEnvironment`,
  `autoescape=True`, `StrictUndefined`, explicit filter/global allowlist, no loader for
  `{% include %}`/`{% import %}`/`{% extends %}`. Publish-time compile + sanitise catches syntax and
  markup problems before an org can break its own documents. Sandboxing alone is not the boundary — the
  renderer controls in §9.1 are.
- **Layouts are print-first CSS**: `@page { size: A4; margin: 18mm 16mm 22mm; }` with `@top-center` /
  `@bottom-right` margin boxes for letterhead and "Page X of Y", repeated `thead` for long tables, no
  JS, no remote assets.
- **Assets**: the logo is loaded from **our own storage bucket** by object path (allowlisted prefix), not
  fetched from an arbitrary URL, then re-encoded and embedded as a `data:` URI. If `logo_url` is an
  external URL, the renderer refuses it rather than fetching it — otherwise the logo becomes an SSRF
  primitive that bypasses the fetcher because it happens in application code, not in WeasyPrint.
- **Reports** build their own context (`ReportContext`: columns, rows, totals) and go through
  `ExportService`'s openpyxl/CSV path for XLSX/CSV, or the same WeasyPrint path for PDF.
- **Sync vs worker**: single-document render inline (target < 1.5 s); report renders and any document
  over ~5 s or > 200 rows go to the existing worker pattern so HTTP requests stay bounded.
- **No AI anywhere in this path.** The OpenAI OCR service is not invoked. That satisfies Q5[f]
  directly and keeps document content inside self-hosted infrastructure.

### 9.1 Rendering security (WeasyPrint is a web renderer, not a template printer)

**Jinja2 sandboxing alone is not sufficient.** `SandboxedEnvironment` limits attribute traversal inside
template expressions; it does nothing about what WeasyPrint does with the resulting HTML/CSS. WeasyPrint
fetches resources, resolves URLs, reads local files and can embed attachments — all after Jinja2 has
finished. The verified behaviour below comes from the upstream Security section of the WeasyPrint docs
and the advisories in `OPEN_SOURCE_RESEARCH.md` §2.3.

| # | Channel | Verified behaviour | Control |
|---|---|---|---|
| 1 | Local file read | Default fetcher opens `file://` URIs from `<img>`, `embed`, `object`, CSS `url()`; **the 10 s HTTP timeout does not apply to `file://`**, and `/dev/urandom`-style files render forever | Deny-all `url_fetcher`; `HTML(string=..., base_url=None)`; render worker filesystem read-only with no app source or secrets mounted |
| 2 | SSRF | Default fetcher also opens `http://`, `https://`, `ftp://` | Custom `URLFetcher.fetch()` that raises `FatalURLFetchingError` for every scheme except pre-registered `data:` assets; no network egress from the render worker |
| 3 | `stylesheets=` / `xmp_metadata=` bypass | CVE-2026-55073: both parameters built a fresh default fetcher, ignoring the configured one; `stylesheets=` is transitive through `@import`/`url()` | **Pin `weasyprint>=70.0`**; never pass a URL or path from a request to either parameter; build `CSS(string=...)` only from our own stylesheet text |
| 4 | External CSS imports | `<link rel=stylesheet>`, `<style>`, `@import`, `@font-face src`, `@color-profile src` all route through the fetcher | Allowlist sanitiser strips `<link>`, `<style>`, `<script>`, `<iframe>`, `<embed>`, `<object>`, `@import`, remote `url()`, `@font-face` with external `src`, `@color-profile`; fetcher denies anything that slips through |
| 5 | PDF attachments | `<link rel=attachment>` / `<a rel=attachment>` attach any reachable file; some viewers execute them (GHSA-35jj-wx47-4w8r) | Sanitiser removes `link`/`a`/`embed`/`object` tags and `rel`/`href`; after render assert `document.metadata.attachments == []`; reject output containing `/EmbeddedFiles` |
| 6 | Untrusted template HTML | Org-authored HTML can carry script, forms, meta refresh, external links | Templates are data, not code: sanitised at **publish**, re-sanitised at **render** (never trust stored rows); tag/attribute allowlist (`p`, `div`, `span`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `h1–h4`, `br`, `strong`, `em`, `ul`, `ol`, `li`, `img` with `data:` only); no event handlers, no `javascript:` |
| 7 | Preview XSS | Returning rendered HTML from `/preview` would execute org-authored script in the app's origin | Preview returns **PDF bytes** (same pipeline as the final render). Any HTML preview surface, if ever added, must be a sandboxed iframe on a separate origin with `Content-Security-Policy: sandbox` — not a shortcut |
| 8 | Resource exhaustion | Docs state long renderings, infinite loops and unlimited CSS integer/float values are real; "restricting HTML document size is not enough" | Caps: HTML ≤ 256 KB after render, rows ≤ 5 000, pages ≤ 200, logo ≤ 2 MB (re-encoded), single image ≤ 4 MB; wall-clock timeout (10 s document, 60 s report) with process kill; worker `ulimit`/container memory cap; one render at a time per worker process |
| 9 | System information leaks | Fonts, library versions, network timing leak through output | Minimal font set in the worker image; generic error codes to callers; render warnings logged server-side only |
| 10 | Tenant isolation | A template or context from org A must be unable to read org B | Template resolved by `(org_id, template_id)` and 404 otherwise; `render_context` built from plain frozen dataclasses (no ORM objects, no lazy loaders); per-render cache (never a process-global cache keyed only by URL); output path `{org_id}/generated/{issued_document_id}.{ext}`; signed URL only after the org check |
| 11 | Jinja2 surface | Sandbox does not stop resource use, and `safe`/`attr` undo escaping | `SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)`; globals replaced with none; filter allowlist `money`, `date`, `qty`, `upper`, `lower`, `default`, `join`, `length` (no `safe`, `attr`, `map`, `selectattr`, `filesizeformat`); `{% include %}`/`{% import %}`/`{% extends %}` disabled by using no loader, not by hoping; publish-time compile + render-time sanitise |
| 12 | Output validation | A compromised render could emit something unexpected | After render: `pypdfium2` page count > 0 and ≤ cap, byte size cap, `file_sha256` recorded, no `/EmbeddedFiles`, expected title present; failure leaves the document in `draft` with an error, never a partial issue |

Process isolation is the backstop: the renderer runs in the worker with a read-only filesystem, no network, a memory limit and a timeout. If every control above failed, the blast radius is one killed worker rather than the API process and its environment.

## 10. Security and isolation

| Requirement (Q5) | Mechanism |
|---|---|
| Tenant isolation | `org_id` on every table, RLS per the 20261012 pattern, `org_id` filter in every repository query, cross-tenant returns 404 |
| Role-based permissions | `require_permission(...)` on every route; two new strings mapped to existing roles |
| Audit logging | `issued_document_events` (+ reconcile with `audit_service`), actor/time/reason on every transition |
| Private storage | Existing `documents` bucket; generated objects at `{org_id}/generated/{issued_document_id}.{ext}` |
| Short-lived links | `StorageService.create_signed_url` (hard cap 300 s) or streamed response with `Content-Disposition` |
| Retention/deletion | Issued artifacts are not deleted through normal workflow; void instead. Draft cleanup after a configurable window. Final retention periods deferred to legal advice, per roadmap |
| No external AI | Render path is local and deterministic |
| No public sharing | No tokenised public route exists in V1 by design |
| SSRF / internal network | Deny-all `url_fetcher`; no egress from the render worker; no caller-supplied URL in `stylesheets=`/`xmp_metadata=` |
| Local file disclosure | Deny `file://`; read-only worker filesystem; no source or secrets mounted (§9.1) |
| Malicious PDF attachments | HTML sanitiser + post-render `attachments == []` and no `/EmbeddedFiles` |
| Stored XSS via preview | Preview returns PDF, never HTML from the app origin |
| Render resource exhaustion | Size/page caps, wall-clock timeout, memory limit, worker isolation |
| Template cross-tenant access | `(org_id, template_id)` lookup with 404; no shared render cache |

Additional hardening: the renderer never accepts a caller-supplied output path; filenames are derived
from `doc_kind` + `document_number`; template HTML is org-scoped and sanitised at publish and at render;
context objects are plain dataclasses, not ORM objects. Full control set in §9.1.

## 11. Reliability and observability

- Render failures never mutate the source record; the draft stays a draft with a visible error.
- `issue` is idempotent on `(org_id, doc_kind, source_id, source_hash)` + caller idempotency key, so a
  retried request cannot mint a second number or a duplicate file.
- Structured logs record `org_id`, `issued_document_id`, `doc_kind`, render duration, page count and
  outcome — never the context body, amounts or party details (matching the existing logging stance).
- Health: rendering is optional at startup. A missing WeasyPrint system library surfaces as a 503 with a
  clear code, not a crash loop for the whole API.

## 12. Frontend surfaces (proposed)

Follows the existing app structure (`frontend/src/app/dashboard/...`, `DashboardLayout`, React Query,
Zod, `src/api/client.ts`, BFF proxy). Interface work must follow `frontend/AGENTS.md` (this Next.js
version differs from older conventions — read `node_modules/next/dist/docs/` before writing code).

| Route | Purpose | Reuses |
|---|---|---|
| `/dashboard/hub` | Issued/draft list, filters by kind/status/date, empty and error states | Existing table + filter patterns from `dashboard/history` |
| `/dashboard/hub/new` | Pick kind → pick source record → preview | Source pickers already used in AP matching |
| `/dashboard/hub/[id]` | Preview, lifecycle timeline, download, void/supersede | `dashboard/document/[id]` layout idioms |
| `/dashboard/settings/company-profile` | Legal name, address, identifiers, logo, footer | Settings patterns from onboarding |
| `/dashboard/settings/document-templates` | Version list, edit, publish, preview | Standard form + confirmation patterns |

Deliberate omissions: no WYSIWYG canvas and no drag-and-drop designer in V1, no public share dialog, no
signature pad. Template editing depends on open decision 1: fixed layouts need no editor at all, and
constrained layouts need only a fields/styles form. If full HTML/CSS editing is approved, the textarea is
privileged (`documents:templates:manage`) and its preview is the **server-rendered PDF**, never the raw
HTML echoed into the app origin.

## 13. Non-goals (explicit)

No AR ledger or customer master; no sales invoices; no statutory or tax filings; no contracts; no
e-signature; no e-invoicing/PEPPOL; no DOCX; no public links; no email delivery of documents; no
independent financial calculation; no posting to accounting providers; no AI summarisation of issued
documents; no multi-language templates; no company bank details stored.

Also excluded as a product claim: **no general ledger, trial balance, statement of account, P&L,
balance sheet or statutory reporting**. AP records are operational data, and reports are extracts over
them (DH-013), not accounting statements.

## 14. Migration and rollout safety

1. Additive migrations only, idempotent, RLS enabled in the same file that creates each table.
2. Seed system templates as data, one per `doc_kind` — so the feature works the moment the API ships,
   with no manual setup. Whether they are seeded per organization or stored as global rows is open
   decision 6; the choice changes the RLS policy and must be made before the migration is written.
3. Backfill nothing. No existing record is rewritten, no `documents` row is touched.
4. Feature flag per org (`features.document_hub`) for pilot rollout, consistent with `Organization.features`.
5. Rollback is dropping the new tables and route registration; no source table is altered.

## 15. Decisions this proposal depends on

Tracked in `DECISIONS.md`: hybrid registry boundary (DH-001), V1 scope (DH-002), snapshot money handling
(DH-003), company profile without bank details (DH-004), numbering and number-at-issue (DH-005),
WeasyPrint with the `>=70.0` security floor and Gotenberg fallback (DH-006), separate registry table
(DH-007), delivery boundary (DH-008), no AI in the render path (DH-009), the unapproved roadmap scope
amendment (DH-010), display-only money formatting (DH-011), retention (DH-012), reports-are-not-a-ledger
(DH-013), and the rendering security boundary (DH-014).

## 16. Open decisions this proposal does not invent answers for

1. Template customisation: fixed layouts vs org-editable templates, and whether "editable" means full
   HTML/CSS or constrained fields on a locked layout.
2. Approval: required second-person approval vs creator issues directly; whether a distinct
   `documents:approve` permission and segregation of duties are needed; whether rejection is editable.
3. Draft editing: presentation fields only vs re-resolving live records; what happens to an approved draft
   when the source changes.
4. Storage and retention: retention window, who may delete, and whether an issued document may ever be
   deleted rather than voided.
5. Navigation: top-level area vs tab inside existing surfaces, and where creation starts.
6. System templates: seeded per organization vs global rows (`org_id is null`), which changes RLS.
7. Expense reports: owner-scoped only, or dropped from V1 until `Expense` has an org association.
8. Source-record deletion: keep the snapshot and mark it orphaned, or refuse the delete.

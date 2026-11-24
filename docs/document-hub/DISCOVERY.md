# Document Hub — Discovery
> **Status:** discovery record. No code, schema, migration, dependency or environment change has been made.
> Everything below was read from the working tree on **2026-11-23**.
> Batch 1 (Q1–Q5) and batch 2 (Q6–Q10) are answered and recorded in §2. Batch 3 (Q11–Q15) is open (§7).

## 1. Where this was inspected

| Item | Value |
|---|---|
| Repository root | `C:\Users\SAMSUNG\documents\invoiai` |
| Branch | `perf/n-plus-one-elimination` |
| HEAD at inspection | `ad39b5d` |
| Working tree | dirty — many unrelated uncommitted changes (auth, repositories, back-button edit). Untouched by this discovery. |

Caveat: `backend/schema.sql` is a 29-line stub that points at `app/migrations`, while the real migration history lives in `backend/migrations/*.sql`. There is no locally applied copy of the full schema, so table-shape facts below come from **domain models plus migration SQL**, not from a live database. Column-level truth must be confirmed against staging before implementation (this is already `PRODUCTION_ROADMAP.md` Phase 0 item 2).

## 2. Confirmed product decisions (from the interview)

These are the answers given, not assumptions:

1. **Hybrid system of record (Q1[b]).** Document Hub owns templates and template versions, generated files and their versions, numbering and internal references, lifecycle/status, approval history and audit events, and access/permissions. Existing financial modules stay authoritative for purchase orders, goods receipts, vendor bills, payments, expenses, balances and financial calculations. Document Hub must never silently change the records it renders.
2. **V1 scope (Q2).** AP-side documents plus reports: purchase orders, goods receipt notes, payment/remittance advice from existing payment records, internal AP summaries, vendor bill cover sheets, AP ageing and spend reports, expense reports where the data exists, plus limited internal letterhead documents. Out of V1: sales invoices and credit notes, tax filings and statutory certificates, contracts and legally binding agreements, HR documents and employee records, customer onboarding and identity documents, e-invoicing and government submissions.
3. **Money handling (Q3[b]).** Read-only snapshots derived from authoritative records. No AR ledger, no independent financial arithmetic that contradicts another module, no posting, no transaction creation. Every rendered document shows its source record and generation timestamp, and preserves the values used at generation time. Draft / approved / issued must be visibly distinct.
4. **Company identity and numbering (Q4, modified [a]).** Add legal/business name, business address, logo and branding, country and currency, existing tax/registration identifiers. **No company bank account details in V1.** Numbering: sequential per organisation and document type, `PO-000001` style; gaps allowed; no annual reset; numbers never reused; voided and cancelled history preserved; internal references kept distinct from statutory invoice numbering.
5. **Delivery (Q5).** PDF yes; XLSX and CSV yes for reports; DOCX later. Public share links no — authenticated access and controlled downloads only. E-signature none in V1. E-invoicing/PEPPOL none in V1. English only. Open-source and self-hostable dependencies preferred, no paid per-document generation APIs, each dependency to be reviewed for licence, security, maintenance and deployment cost.
6. **Security baseline.** Tenant isolation, role-based permissions, audit logging, private file storage, short-lived authenticated download links, retention and deletion controls, and **no sensitive document content sent to external AI providers by default**.
7. **Template customisation (Q6[b], accepted).** Fixed, centrally maintained layouts with **controlled
   organisation-level customisation**: logo, brand colours, company information, header and footer,
   permitted labels/explanatory text/notes, and optional terms blocks. **No arbitrary HTML, CSS or
   JavaScript template editing in V1.** Organisation administrators control branding and permitted
   template settings. Basic branding is available to paying organisations; advanced customisation may
   become a paid-plan feature later — **pricing and tier boundaries remain open**. System templates stay
   centrally maintained and are specialised per organisation through settings or controlled overrides;
   one organisation must never affect another's templates.
8. **Approval (Q7, accepted).** Approval rules are configurable **by document type and, where
   appropriate, financial threshold**. Whenever approval is required: the creator cannot approve their
   own document; approval happens **before issue and before final number assignment**; rejection returns
   the document to an editable draft and records the reason; a dedicated `documents:approve` permission
   gates the act; and creator, approver, timestamps and decisions are written to audit history. A second
   approval is **not** required for every document. Existing source-workflow approvals are reused where
   they already provide the control, and duplicate PO/payment approval workflows are not created. A
   remittance advice reflects an authoritative payment record and generating it **never authorises or
   executes a payment**. **The exact approval matrix and thresholds remain open** pending research
   against existing InvoiAI workflows.
9. **Editing and source change (Q8, accepted).** Editable: permitted presentation fields, notes and other
   document-only fields. Locked: financial values, quantities, source identifiers and calculated totals,
   which stay controlled by the authoritative source record. Drafts may be refreshed from source. Once
   issued, the document **and its generated file are immutable**. If the source record later changes, the
   document shows a visible **source-changed warning**; an authorised user may deliberately create a
   replacement or revised document; the original is preserved, the version relationship is recorded, and
   every action is audited. Silent regeneration or overwrite is forbidden. **Revision numbering is not
   one universal rule** — appropriate behaviour is to be researched per document type (open).
10. **Retention, deletion and customer exit (Q9[c], accepted).** Retention is configurable at
    organisation level, subject to legal and contractual requirements. Legal holds prevent deletion.
    Ordinary users cannot casually delete issued documents. **Voiding and deletion are distinct
    operations.** Drafts may have shorter retention. Customers can export their issued documents and
    associated metadata when leaving InvoiAI. The issued file is stored with the resolved source snapshot
    and integrity hashes. Retention and deletion operations are permission-controlled and audited.
    **Jurisdiction-specific retention periods remain open**, and indefinite retention is not assumed to
    be lawful in every market.
11. **Navigation and first run (Q10[c], accepted).** A **standalone top-level Documents area** for
    searching, filtering, viewing and managing generated documents, **plus contextual generation actions**
    inside purchase order, goods receipt and payment workflows. Draft-first with preview; approval where
    configured; issue only after validation and all required approvals. Received documents (Document
    Intelligence) and generated documents (Document Hub) are visibly distinct. Visibility and actions are
    enforced through explicit permissions — `documents:view` plus create, edit, approve, issue, void and
    download.

## 3. What already exists (verified)

### 3.1 Document intake and processing

- `backend/app/models/domain/document.py` — `Document` mirrors the `documents` table: `file_url`, `file_name`, `file_type`, `file_size_bytes`, `file_hash`, extracted header fields, amounts, `status`, `pipeline_stage`, `validation_warnings`, export bookkeeping (`sheets_url`, `last_exported_at/format/by`), archive fields (`is_archived`, `archived_at/by`, `archive_reason`), `notes`.
- `backend/app/core/enum/database.py` — `DocumentType` has 17 values including `invoice`, `credit_note`, `debit_note`, `purchase_order`, `quotation`, `delivery_note`, `expense_report`, `receipt`, `spreadsheet`, `unknown`. `DocumentStatus` has 10 values (`pending`, `ocr_running`, `ocr_complete`, `analysis_running`, `needs_review`, `in_approval`, `approved`, `rejected`, `failed`, `quarantined`). These describe **inbound** documents.
- `backend/app/routers/documents.py` — upload, list, workflow, intelligence, capture options/PATCH, analyze, review, OCR, delete.
- OCR is OpenAI-based (`backend/app/integrations/openai/openai_ocr_service.py`).

**Relevance:** the `documents` table is an *inbox*. It has no version, template, rendered-artifact or number-series concept, and `DocumentStatus` describes extraction progress, not issuance. Reusing it for outbound documents would overload one table with two unrelated lifecycles.

### 3.2 AP records that can be rendered

| Record | Model | Notable fields for rendering |
|---|---|---|
| Purchase orders | `backend/app/models/domain/purchase_order.py` | `po_number`, `org_number`, `amount`, `currency`, `issued_date`, `expiry_date`, `is_open`, `matched_amount`, `description`, `metadata` (line items stored in `metadata.line_items` when created from a document, see `backend/app/routers/ap.py`) |
| PO lines | `backend/migrations/20261110_purchase_order_lines_and_atomic_receipts.sql` | line table plus `purchase_order_lines` and atomic receipt functions |
| Goods receipts | `backend/app/models/domain/ap.py` — `GoodsReceipt`, `GoodsReceiptLine` | `receipt_number`, `received_at`, `status`, `notes`; lines carry `description`, `sku`, `quantity_ordered`, `quantity_received`, `quantity_accepted`, `quantity_rejected`, `unit_of_measure`, `unit_price`, `warehouse_location` |
| Vendors | `backend/app/models/domain/vendor.py` | `name`, full postal address (`address_line1/2`, `city`, `state`, `postal_code`, `country`), `tax_id`, `registration_number`, `bank_name`, `bank_account_hash`, plus AP policy fields |
| Payments | `backend/app/models/domain/payment.py` | `payment_number`, `payment_method`, `amount`, `currency`, `payment_date`, `status`, `reference` |
| Payment instructions | `backend/app/models/domain/ap.py` — `PaymentInstruction`, `PaymentInstructionEvent` | `amount`, `currency`, `payment_method`, `scheduled_date`, `status`, `approved_by`, `authorized_by`, `metadata`; events carry `from_status`/`to_status`/`actor_id`/`reason` |
| Bills / coding / tax | `backend/app/models/domain/ap.py` — `InvoiceCoding`, `TaxCode`, `ChartOfAccount`, `AccountingDimension` | GL code and department/cost-centre/project attribution for report columns |
| Expenses | `backend/app/models/domain/finance.py` — `Expense` | `amount`, `currency`, `description`, `category`, `expense_date`, `document_id`; owned by `owner_type`/`owner_id`, not `org_id` |

### 3.3 Numbering that already exists

`backend/migrations/20261110_purchase_order_00_org_number.sql` is the reference implementation and it already matches the numbering rules chosen in Q4:

- `purchase_order_number_counters (org_id primary key, prefix, last_number, updated_at)`.
- `next_purchase_order_org_number(uuid)` returns `PO-` + `lpad(...,6,'0')`, i.e. `PO-000001`.
- The upsert is atomic, so concurrent inserts serialise on the primary key instead of issuing duplicate numbers.
- A `unique (org_id, org_number)` partial index protects uniqueness; a trigger assigns the number when absent.
- No annual reset, and no attempt to reclaim numbers from deleted rows — matching "gaps allowed, never reuse".

Goods receipts already receive a `receipt_number` at creation (`backend/app/routers/ap.py`), but from the caller's document number rather than a dedicated series.

### 3.4 Export today

- `backend/app/routers/export_v2.py` exposes `GET /export/{document_id}/excel`, `GET /export/{document_id}/csv`, `POST /export/{document_id}/sheets`.
- `backend/app/services/export/exporter_service.py` dispatches only `excel`, `csv`, `google_sheets`; anything else raises `Unsupported export format`.
- A repository-wide search for `reportlab`, `weasyprint`, `fpdf`, `pdfkit` returns **no generation code**. Every `application/pdf` hit is PDF as *input* (upload, OCR, extraction, storage validation).

**There is no PDF generation anywhere in the codebase.** This matters because `docs/PRODUCTION_ROADMAP.md` Phase 0 item 3 requires verifying "the MVP's approved-invoice CSV/PDF handoff" and round 10 lists "payment-instruction export" as launch scope. The CSV half exists; the PDF half does not.

### 3.5 Storage and file handling

`backend/app/services/storage/storage.py`:

- Single `documents` bucket, private.
- `upload_document` / `upload_and_verify` (upload then re-download to prove the object exists, best-effort cleanup on failure), `delete_document`, `exists`, `verify_document`.
- `create_signed_url` with `MAX_SIGNED_URL_SECONDS = 300` and hard rejection above that. This already satisfies "short-lived authenticated download links".
- Storage SDK calls are pushed off the event loop via `run_db`.

`backend/app/services/storage/attachment_scanner.py` provides quarantine and signature checks for inbound files; generated files are produced by us, so they need no inbound scanner, but they do need the same bucket and the same path discipline.

### 3.6 Organisation identity today

`backend/app/models/domain/organization.py`:

- `Organization`: `name`, `slug`, `plan`, `industry`, `country`, `currency`, `tax_id`, `logo_url`, `website`, `features`, `document_limit`.
- `OrganizationSettings`: `default_currency`, `supported_currencies`, `timezone`, `fiscal_year_start_month`, `date_format`, `number_format`, `default_language`, `brand_color`, `custom_domain`, approval/AI/duplicate policy.

**Missing for a customer-facing document:** postal address (any lines, city, region, postcode), legal entity name distinct from display name, registration number beyond `tax_id`, phone/email on the letterhead, footer/terms text. This confirms Q4's "modified [a]": a small company-profile addition is required, and bank details are not.

Also relevant: `Vendor.bank_account_hash` proves the codebase deliberately stores only a hash of bank account numbers. Do not add plaintext company bank details to the profile in V1 — it would contradict an existing security pattern.

### 3.7 Permissions, isolation, audit

- `backend/app/core/permissions.py` exposes granular permission strings (`documents:view`, `vendors:manage`, `finance:manage`, `roles:manage`, …) consumed through `require_permission(...)`.
- `backend/app/routers/export_v2.py` shows the house pattern: `require_verified_user` at router level, `require_fresh_mfa` on download-y routes, `limiter.limit("10/minute")`, org check via `get_org_context`, and an explicit `doc.org_id != ctx.org_id → 404`.
- `backend/migrations/20261012_tenant_isolation_rls_and_audit_indexes.sql` establishes RLS plus audit indexes; any new table must follow it.
- `backend/app/services/audit_service.py` is a generic event sink (confirmed: `log(org_id, user_id, action, resource_type, resource_id, old_values, new_values, request_id, ip_address, user_agent, ai_triggered)`).

### 3.8 Frontend surfaces today

- `frontend/src/app/dashboard/history/page.tsx` — document list.
- `frontend/src/app/dashboard/upload/page.tsx` — intake.
- `frontend/src/app/dashboard/document/[id]/page.tsx` — detail/review, renders source PDF via signed URL, `isPdf` handling at line ~326.
- `frontend/src/app/api/bff/[...path]/route.ts` — BFF proxy; `frontend/src/api/client.ts` — API client.
- No hub, no template editor, no issued-document list, no company-profile form, no print/preview surface for POs, receipts or payment instructions.

### 3.9 Report data availability (verified field by field)

Requirement: reports must only present information the authoritative records actually hold, and must not
read as a complete accounting ledger. The fields below were read from the domain models; whether they are
populated in practice is a staging question (Phase 0).

| Report | Fields that exist today | What is genuinely missing |
|---|---|---|
| AP ageing | `documents.due_date`, `document_date`, `total_amount`, `paid_amount`, `balance_due`, `payment_status`, `currency`, `vendor_name`; recorded allocations (`payment_allocations`, `document_match_allocations`) | No GL, no journal, no accrual/cash basis, no period close. `due_date` is optional and extraction-dependent. There is no single authoritative "amount still owed" beyond `balance_due` as recorded. |
| Spend summary | `documents.total_amount`, `tax_amount`, `currency`, `vendor_name`; `invoice_codings` for GL/department/cost-centre attribution; `vendors` | No committed vs actual, no budget, no FX revaluation. Coding may be absent for uncoded bills. |
| Vendor activity | `vendors`, `purchase_orders` (`amount`, `issued_date`, `is_open`), `goods_receipts` | No statement of account, no credit-terms interest. `vendor_credits` exists but is out of V1 scope. |
| Payment position | `payment_instructions` (`amount`, `currency`, `status`, `scheduled_date`), `payments` (`amount`, `payment_date`, `status`, `reference`) | No bank reconciliation, no cleared funds. `status` is InvoiAI workflow state, not bank state. |
| Expense report | `Expense.amount/currency/category/expense_date/description/document_id` | **`Expense` has `owner_type`/`owner_id`, not `org_id`** (`finance.py` lines 16–19). An org-wide expense report cannot be produced from the current model; only the requesting owner's records are supported. |

Consequences recorded for the architecture: every report must print its **included population, the fields
it depended on, and the count of records excluded for missing data**, and must carry a plain disclaimer
that it is derived from records held in InvoiAI, not a statement of account or a complete ledger. Any
report that cannot be computed from the fields above is out of scope, not implemented approximately.

### 3.10 Approval, numbering, retention and permissions as they actually exist

Batch 2 depends on existing mechanisms. They were re-read on 2026-11-23; several do **not** work the way a
naive plan would assume.

| Area | What the code actually does | Consequence for the hub |
|---|---|---|
| Approval workflow | `approval_workflows` is keyed by `document_id`/`analysis_id` and carries `document_amount`, `vendor_name`, `document_type`, `workflow_type` (`backend/app/models/domain/approval.py` 61-104). `ApprovalWorkflowType` has only `BILL` and `PAYMENT` (`core/enum/ap.py` 91-94). | Not polymorphic. A generated document cannot attach to this table without a schema change; the engine cannot simply be pointed at `issued_documents`. |
| Approval authority | `approval_authorities` has `CHECK (approval_type IN ('invoice','payment'))` (`migrations/20260926_industry_standard_org_approval_controls.sql` line 30), per-currency `limit_amount`, `can_self_approve`, `can_approve_exceptions`. | A hub approval type requires a migration on an existing AP table. Thresholds and delegation are otherwise reusable in shape. |
| Segregation of duties | `sod_rules(org_id, rule_key, enabled)`; `SegregationOfDutiesService.enabled()` returns **false when no row exists**. `validate_invoice_approval` reads `documents.created_by` and is invoice-specific. | "Creator cannot approve" cannot be inherited by default - existing orgs have the rule **off** unless configured. The hub must enforce it itself. `can_self_approve` on an authority row would otherwise contradict the accepted rule. |
| Purchase order approval | **None.** `purchase_orders` has no approval state; the `status` field is integration sync status (`models/domain/purchase_order.py`). | "Reuse source-workflow approvals where they exist" is true for bills and payments and **false for POs**, which is the most common V1 document. |
| Payment approval | `PaymentInstructionStatus` has a full lifecycle including `pending_approval`, `approved_for_payment`, `pending_authorization`, `authorized`, plus `approved_by`/`authorized_by`. | A remittance advice can safely render only an already-authorised or paid instruction; the hub adds no authority of its own. |
| PO identity | `purchase_orders` already holds **two** numbers: provider `po_number` and InvoiAI `org_number` (`PO-000001`), unique per org (`migrations/20261110_purchase_order_00_org_number.sql`). | A hub `PO` series would mint a second, different `PO-000001`. The document must render `org_number` and the hub must not open a competing series. |
| Goods receipt identity | `receipt_number` is derived from the caller's document number at creation; there is no receipt series. | Two receipts from the same source document cannot be told apart by number. Revision identity needs deciding, not assuming. |
| Retention | `organization_settings` policy JSON contains `document_retention_months: 84`, `ocr_retention_months: 84`, `ai_data_retention_months: 24`, `audit_log_retention_months: 84`, `deleted_document_retention_days: 30` (`routers/organization_settings.py` 195-201), editable in the settings UI. **No job, worker or service reads these values.** There is no legal-hold concept anywhere. | Retention is currently a stored preference, not behaviour. The hub cannot join an existing retention job because none exists, and must not add a second, contradictory retention setting beside the one already exposed. |
| Permissions | `core/permissions.py` plus per-organisation `organization_roles.permissions` JSONB seeded from the 20260926 migration with `ON CONFLICT DO NOTHING`. `documents:view` is granted to `viewer`, `ap_member`, `ap_manager`, `finance_manager`. `approvals:approve` exists for inbound documents. There is **no** `documents:approve`, `documents:issue`, `documents:void` or `documents:download`. | New permission strings do not reach already-created organisations automatically; role rows need a backfill. `documents:view` is already the inbound-document permission, so shared use widens who can see generated documents. |
| Branding | `organization_settings` already carries a `branding` block (email/portal/sender) and the org row has `logo_url`, `brand_color`, `settings.date_format`, `number_format`, `default_currency`. | Q6 needs no new branding store - it needs a template-settings layer beside what exists. |
| Audit | `AuditService.log(...)` is generic and `audit_logs` is indexed by org/actor/resource/time. | Already settled: compliance trail in `audit_logs`, UI timeline in hub events. |

**Contradictions found and how they are recorded, not resolved silently.**

1. DH-005's prefix map allocates `PO` and `GR` to hub kinds, while the same entry says PO and goods-receipt
   documents reuse the source record's number. Both cannot be true. The map is corrected here to reserve
   `PO`/`GR` as **source-owned, never minted by the hub**, and the revision-identity question is opened.
2. Absolute creator-must-not-approve conflicts with `can_self_approve` on authority rows and with
   `no_self_approval` being **off by default**. The accepted rule wins for hub documents; the authority
   flag is ignored on that path. This is a deliberate divergence, recorded rather than quietly coded.
3. `documents:view` now means both "see received documents" and "see generated documents". Accepted for
   V1, but it means a read-only viewer sees generated documents too. Recorded as a consequence, with a
   namespaced alternative left open.
4. Q7 asks for approval before issue, but POs have no approval state at all, so a generated PO either
   needs a hub-owned approval or a new PO approval workflow in the AP module. Not decided here.

Impact: the two heaviest constraints are that **the existing approval engine cannot be reused unchanged**
and that **retention has no enforcement layer to plug into**. Both change effort and sequencing.

## 4. What is reusable, and what genuinely is not

**Reusable as-is**

- `StorageService` - bucket, signed URLs cap, upload-and-verify.
- `ExportService` - Excel/CSV path for reports (openpyxl already present), and the `ExportResult` shape.
- Permission strings, `require_permission`, `require_fresh_mfa`, rate limiting, org-context check, 404-on-cross-tenant pattern.
- `purchase_order_number_counters` + `next_purchase_order_org_number()` as the numbering design to generalise.
- `document_line_items`-style line modelling, and existing PO/receipt/payment-instruction row shapes as snapshot sources.
- RLS/audit migration pattern, `audit_service`.
- Frontend layout, React Query, Zod, BFF proxy, existing table/empty/error patterns.

**Not reusable, must be new**

- Any PDF renderer (none exists).
- A template store with versions (`document_templates` equivalent) - nothing like it exists.
- An issued-document registry with lifecycle distinct from OCR status - `documents.status` cannot carry `issued`/`voided`/`superseded` without corrupting intake semantics.
- Snapshot immutability - nothing freezes rendered inputs today.
- Company postal/legal identity fields.
- Generic per-type number series (PO counters are PO-only and SQL-function-bound).
- An approval path for generated documents (the existing engine is bill-shaped; §3.10).
- A retention enforcer or legal-hold mechanism (settings exist; behaviour does not; §3.10).

**Explicitly out of V1, per answers:** customers/AR, sales invoices, e-invoicing, e-signature, public links, DOCX, multi-language documents, external AI in the render path, company bank details.

## 5. Tension with the existing roadmap (recorded, not resolved silently)

`docs/PRODUCTION_ROADMAP.md` "Deferred capabilities" contains:

> Shared document generator beyond invoice PDF - §2.5 - **Deferred** - Reconsider when: Paying customers require a second generated document type.

Read strictly, the chosen V1 scope (PO, goods receipt, remittance advice, cover sheets, reports, letters) **is** a second and third generated document type, so this plan crosses a line the roadmap drew. Three facts make the crossing defensible, and all of them should be stated in `DECISIONS.md` rather than glossed over:

1. Phase 0 item 3 already requires a **PDF** handoff for payment instructions, which does not exist. Some rendering capability is already launch scope.
2. The roadmap's own positioning rules forbid claiming to be an accounting system, tax platform or e-invoicing solution - the proposed V1 stays inside that boundary by rendering only AP-side operational documents and read-only snapshots.
3. The trigger is measurable: the V1 keeps the generator to AP records that already exist, with no AR and no new financial calculation.

`DECISIONS.md` records this as an explicit scope amendment that needs product-owner sign-off, not as an engineering detail. **`docs/PRODUCTION_ROADMAP.md` itself is not edited by this plan** - the conflict stays visible until a product owner resolves it in their own change.

## 6. Assumptions that remain unverified

| Assumption | Why it is unverified | How to settle it |
|---|---|---|
| Live `purchase_orders`, `goods_receipts`, `payment_instructions` column sets match the domain models | No local database; `schema.sql` is a stub | Compare migrations to staging (Phase 0 item 2) |
| RLS policies cover every table the hub reads | Only the 20261012 isolation migration was read, not staging state | Query staging `pg_policies` |
| WeasyPrint renders identically and within budget on the deployed image | Not installed; no rendering performed | Phase 0 spike with the security fixtures |
| Fonts available in the runtime image cover the letterhead design | No image inspection done | Inspect `backend/Dockerfile` during the spike |
| Report fields (`due_date`, `balance_due`, coding rows) are populated for a usable share of real bills | Models allow them; extraction may leave them null | Count nulls per field on staging (Phase 0) before promising an ageing report |
| Issued documents survive a deliberate adversarial template | No hostile template tested yet | Phase 0 security fixtures (fetcher, attachments, CSS values) |
| Existing organisations' `organization_roles.permissions` rows pick up new hub permissions | Seed migration uses `ON CONFLICT DO NOTHING`; per-org edits already possible | Inspect staging role rows; plan an additive backfill |
| A generated PO can reuse the existing AP approval workflow | `approval_workflows` is `document_id`-keyed and bill-shaped (§3.10) | Decide in batch 3 whether PO approval is hub-owned or AP-owned |
| `retention` settings are enforced somewhere | No reader of the keys was found outside the settings router and UI | Confirm no cron/worker outside the read scope |

## 7. Questions that still need an answer before implementation (batch 3)

Batch 1 answered scope, money handling, delivery and packaging. Batch 2 answered templates, approval,
editing, retention and navigation. These five are the next frontier (also listed in `DECISIONS.md` §Open
questions).

1. **Document identity and numbering** - a generated PO could carry the PO's existing `org_number`, or a
   separate hub document number. Which is the vendor-facing reference? What number does a revision take,
   and does goods receipt need a series where `receipt_number` is currently copied from the source?
2. **Who uses this** - which roles, team sizes and customer segments generate, approve and receive these
   documents? Is the buyer the only audience, or does the vendor/AP contact matter in V1?
3. **Bulk and scale** - is bulk generation a V1 requirement (year-end remittance runs, all open POs, a
   vendor's whole history)? What must search and filtering cover?
4. **Delivery and sharing** - download only, or email from the hub? Who is the sender, what happens on
   bounce, and what is stored about the recipient?
5. **Currency, locale and country requirements** - multi-currency organisations, document date/number
   formatting, and whether any target country needs a field we do not hold (VAT number placement, legal
   footer text).


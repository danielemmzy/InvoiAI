# Document Hub — Decision Log

Format: one record per decision, with status, context, decision, consequences and a revisit trigger.
"A — accepted" means the product owner chose it in the discovery interview. "P — proposed" means
engineering recommends it and it is awaiting approval. "O — open" means it needs an answer.

---

## DH-001 — Hybrid ownership: registry yes, ledger no

**Status:** A — accepted (Q1[b]) · 2026-11-23

**Context.** The codebase has real AP records (`purchase_orders`, `goods_receipts`,
`payment_instructions`, vendor bills) but no customers table and no AR ledger. A document feature can
either sit above those records or become a second authority for the same facts.

**Decision.** Document Hub owns templates and template versions, generated files and versions, numbering
and internal references, lifecycle and status, approval history and audit events, and access
permissions. Existing financial modules remain authoritative for POs, goods receipts, vendor bills,
payments, expenses, balances and calculations. The hub never writes financial values back.

**Consequences.**
- The hub cannot be used to "correct" a PO amount; corrections happen in the owning module and are
  superseded by a new issued document.
- Every rendered document prints its source record and generation timestamp.
- The `documents` inbox table keeps its meaning; nothing about intake changes.

**Revisit when** an AR module, customer master or ledger is built — at that point the boundary needs
re-drawing, not extending by habit.

---

## DH-002 — V1 covers AP-side documents and reports only

**Status:** A — accepted (Q2) · 2026-11-23

**In V1:** purchase orders, goods receipt notes, remittance advice from existing payment records,
internal AP summaries, vendor bill cover sheets, AP ageing and spend reports, expense reports where data
exists, and limited internal letterhead documents.

**Out of V1:** sales invoices and credit notes, tax filings and statutory certificates, contracts and
legally binding agreements, HR and employee documents, customer onboarding and identity documents,
e-invoicing and government submissions.

**Consequences.** No customer entity is introduced. No document in V1 is a demand for payment from a
customer, so no receivables control is implied. Statutory numbering stays out of scope, which is why
internal references are explicitly distinct from statutory invoice numbers.

**Revisit when** a paying customer requests receivables (matches the roadmap's AR trigger).

---

## DH-003 — Financial values are read-only snapshots

**Status:** A — accepted (Q3[b]) · 2026-11-23

**Decision.** The hub renders values copied from authoritative records at snapshot time. No new AR
ledger, no independent calculation that could contradict another module, no posting, no transaction
creation. Each document shows source record and generation timestamp, preserves the values used, and
distinguishes draft / approved / issued.

**Consequences.**
- Adapters copy `subtotal` / `tax` / `total` where the source stores them; where the source stores only a
  single amount, the document shows that amount and no invented breakdown.
- A source record that changes after issuance does not change the document. The UI reports drift and
  offers supersede.
- No reconciliation logic lives in this feature; a mismatch is a source-module issue.

**Revisit when** the product gains a computed-reporting layer with its own verified arithmetic.

---

## DH-004 — Add a company document profile; do not store bank details

**Status:** A — accepted (Q4, modified) · 2026-11-23

**Context.** `organizations` has `name`, `tax_id`, `logo_url`, `country`, `currency` and
`OrganizationSettings.brand_color` — but no postal address, no legal-entity name, no registration
number, no letterhead contact text. `Vendor` deliberately stores `bank_account_hash`, never a plaintext
account number.

**Decision.** Add legal/business name, business address, logo and branding, country and currency,
existing tax/registration identifiers, and letterhead contact/footer text. Do **not** collect or store
company bank account details in V1.

**Consequences.** Customer-facing AP documents (PO, remittance advice) can carry a proper letterhead.
Any future feature that needs company banking details must justify it explicitly and follow the existing
hash-only precedent.

**Revisit when** a specific approved feature (e.g. a customer-facing invoice with payment instructions)
requires bank details — then with a security review, not as a profile field.

---

## DH-005 — Internal numbering: per org and kind, six digits, no reset, no reuse

**Status:** A — accepted (Q4) · number-at-issue is **P — proposed**

**Decision.** Sequential per organisation and document type, format `PREFIX-000001`, gaps allowed, no
annual reset, numbers never reused, voided/cancelled history preserved, internal references kept
distinct from statutory invoice numbering.

**Numbering guarantees (required, not optional).**

- **Atomic** — one `insert … on conflict do update` on the `(org_id, doc_kind)` primary key; concurrent
  issues serialise in the database. Generalises the existing `next_purchase_order_org_number(uuid)`
  rather than inventing a new mechanism.
- **Unique** — `unique (org_id, prefix)` on the series, `unique (org_id, document_number)` on issued rows;
  a second kind cannot claim a prefix already in use, which would otherwise collide at issue time.
- **Never reused** — the counter is monotonic and never reset or decremented; no code path takes `min` or
  `count`; issued rows are not deletable through the application.
- **Gaps permitted** — a rolled-back issue leaves a hole with no row and no event. That is the accepted
  cost of assigning inside the transaction; it is not a defect and no backfill is attempted.
- **Auditable** — the `issued` event carries number + hash, the series row keeps `last_number` and
  `updated_at`, the issued row keeps `issued_at`/`issued_by`, and `AuditService` writes a compliance
  entry. Four independent records agree.
- **Assigned at issue, not at draft** — abandoned drafts consume no number. *This refinement still needs a
  yes/no; the rest is settled.*

**Prefix map is explicit, not derived, and only covers kinds the hub owns.** `remittance_advice→REM`,
`vendor_bill_cover→COV`, `ap_summary→SUM`, `ap_ageing_report→AGE`, `spend_report→SPD`,
`expense_report→EXP`, `letter→DOC`. `purchase_order` and `goods_receipt` are **source-owned** and appear
in no map: `PO-000001` is already a live InvoiAI series (`purchase_order_number_counters`), so a hub `PO`
series would mint a second document with the same number. Deriving with `left(doc_kind, 2)` produces `PU`
and gives two report kinds the same prefix — a real bug avoided, not a style preference.

**Consequences.** A voided document keeps its number permanently. Purchase order and goods-receipt
documents reuse the source record's existing `org_number` / `receipt_number` instead of burning a second
series, so their issued rows carry **no hub number** and the `issued_number_required` constraint must
exempt source-owned kinds. Whether a revision reuses or replaces that reference is Q11, not assumed here.
The SQL function is executable only by `service_role`, matching the PO generator; clients cannot mint
numbers directly.

**Revisit when** an organisation asks for annual reset or per-department series — both are configuration
changes, not redesigns, but must be decided before launch because they change uniqueness scope.

---

## DH-006 — PDF engine: WeasyPrint in-process, Gotenberg as documented fallback

**Status:** P — proposed · 2026-11-23

**Evidence.** WeasyPrint is BSD-3-Clause (verified from upstream `LICENSE`, `pyproject.toml`, PyPI
classifiers); ReportLab's open-source toolkit is BSD but sits next to a paid PLUS/RML product; Gotenberg
is MIT (verified from upstream `LICENSE` and its site); pypdfium2 is Apache-2.0/BSD-3 and is already a
pinned dependency. Full detail in `OPEN_SOURCE_RESEARCH.md`.

**Decision.** Render Jinja2 HTML/CSS with WeasyPrint in-process, **pinned to `weasyprint>=70.0`**; use the
already-installed `pypdfium2` for page count and sanity checks; keep Gotenberg documented as the fallback
if the Phase 0 spike shows a fidelity or throughput failure.

**Why the floor is 70.0.** CVE-2026-55073 / GHSA-jf6q-chmf-3h3v (published 2026-09-08) showed that
`write_pdf(xmp_metadata=[url])` and `write_pdf(stylesheets=[url])` bypassed a configured `url_fetcher`,
allowing arbitrary local file reads and SSRF through the CSS import graph. Patched only in 70.0. Pinning
is necessary but not sufficient: those parameters must never receive caller-influenced values, and a
deny-all fetcher plus sanitised HTML is still required (DH-014).

**Consequences.** No extra container, no browser in the image, one failure domain. Layouts must be written
as print CSS (no flex/grid exotica), and large reports go to a worker. The Docker image needs WeasyPrint's
system libraries — Phase 0 exists to prove that before Phase 1 starts.

**Revisit when** the spike fails, or measured throughput on real customer documents misses the target.

---

## DH-007 — A separate registry table, not a new status on `documents`

**Status:** P — proposed · 2026-11-23

**Context.** `documents` carries intake semantics (`ocr_running`, `needs_review`, `pipeline_stage`,
archive flags) and every existing query depends on that meaning. Outbound documents need
`draft/approved/issued/voided/superseded`, a number, template versions and frozen bytes.

**Decision.** New `issued_documents` table plus `document_templates` and `issued_document_events`, with a
nullable link back to the source record. `documents` is untouched.

**Consequences.** Two concepts must be named clearly in the UI (received documents vs issued documents).
Existing intake queries stay correct without a discriminator. Rollback is dropping new tables.

**Revisit when** someone proposes merging them "to reduce tables" — the answer is in this record.

---

## DH-008 — Delivery boundary: PDF/XLSX/CSV only, authenticated only, English only

**Status:** A — accepted (Q5) · 2026-11-23

| Capability | V1 |
|---|---|
| PDF | Yes |
| XLSX / CSV (reports) | Yes |
| DOCX | Later |
| Public share links | No — authenticated access, controlled downloads |
| E-signature | None |
| E-invoicing / PEPPOL / fiscal formats | None |
| Languages | English |

**Consequences.** No tokenised public route is built, so nothing can be leaked by a forwarded link. Any
document that would legally need a signature is out of V1 by DH-002. Downloads use
`StorageService.create_signed_url` (300 s cap) or a streamed response, behind fresh MFA and a rate limit.

**Revisit when** a customer needs to send a PO or remittance advice to a supplier — that is an email
delivery and sharing decision, and it needs its own security review.

---

## DH-009 — No external AI anywhere in the render path

**Status:** A — accepted (Q5[f]) · 2026-11-23

**Decision.** Rendering is deterministic and local: snapshot → template → PDF. The OpenAI integration used
for OCR is not invoked, and no document content leaves the deployment for generation. Operators can
optionally add notes themselves; the system does not summarise issued documents.

**Consequences.** No privacy exception is needed for the feature. This also means no "AI-written letter"
convenience in V1 — a deliberate trade.

**Revisit when** the product has an explicit, reviewed privacy posture for sending document content to a
model, with per-org consent.

---

## DH-010 — Explicit scope amendment to the production roadmap

**Status:** O — **blocked**; needs product-owner sign-off before Phase 1

**Context.** `docs/PRODUCTION_ROADMAP.md` "Deferred capabilities" lists:

> Shared document generator beyond invoice PDF — §2.5 — **Deferred** — Reconsider when: Paying customers
> require a second generated document type.

The approved V1 (DH-002) generates PO, goods receipt, remittance advice, cover sheets, reports and
letters — several document types beyond an invoice PDF. Meanwhile Phase 0 item 3 already requires
verifying "the MVP's approved-invoice CSV/PDF handoff", and no PDF generator exists in the codebase, so
some rendering capability is already launch scope.

**This planning work does not edit `docs/PRODUCTION_ROADMAP.md`.** The conflict is recorded here and left
visible; changing production roadmap scope is the product owner's action, not an engineering consequence
of writing a design document.

**Decision required.** Either (a) accept this as a documented amendment with the trigger "AP launch needs
printable PO / receipt / remittance documents, and the PDF half of the payment handoff is missing", or
(b) narrow V1 to the single document the launch gate already requires (payment-instruction PDF) and defer
the rest. Until one is chosen, only Phase 0 (spike, no product code) may proceed.

**Consequences of (a).** The product owner updates the roadmap text in their own change, with the
amendment recorded — not left contradicting the shipped code. **Consequences of (b).** Phase 1 shrinks to
one `doc_kind`; templates, company profile and template management mostly remain because the PDF still
needs a letterhead.

**Revisit when** this is signed off; until then Phase 0 only (spike, no product code).

---

## DH-011 — Money formatting and rounding stay display-only

**Status:** P — proposed · 2026-11-23

**Decision.** Amounts are carried as `Decimal` from the source record, formatted by a template filter for
presentation only. The hub performs no rounding, currency conversion, tax computation or re-totalling. If
a source stores a value with more precision than displayed, the stored value is preserved in
`render_context`.

**Consequences.** The PDF can never disagree with the source record about a total. FX behaviour remains
the source module's responsibility, consistent with the roadmap's "do not silently convert" rule.

---

## DH-012 — Retention: keep issued artifacts, clean drafts

**Status:** **superseded by DH-019** (Q9 answered the policy; Q9[c] added legal hold, export on exit and
audited deletion) · proposed 2026-11-23, superseded 2026-11-24

Kept for the original reasoning: drafts carry no legal or audit meaning and may expire on a short window;
issued artifacts are not deleted by ordinary workflow; voiding marks rather than deletes. DH-019 replaces
the deferred-policy posture with an accepted one.

**Decision.** Issued PDFs and their `render_context` are retained and are not deleted through normal
workflow; voiding marks and watermarks them. Drafts that are never issued are cleaned up after a
configurable window (default 30 days) because they carry no legal or audit meaning.

**Consequences.** Final retention periods remain deferred to legal advice, per the roadmap — this entry
sets behaviour, not a legal commitment. A deletion request for a source record does not automatically
delete an issued document; that requires an explicit, audited decision.

**Revisit when** legal review returns retention periods.

---

## DH-013 — Reports are operational extracts, never a ledger

**Status:** P — proposed · 2026-11-23

**Context.** V1 includes AP summaries, ageing and spend reports. InvoiAI holds bills, codings, purchase
orders, goods receipts, payment instructions and payments — it holds **no general ledger, journals,
accruals, period close, bank reconciliation or FX revaluation**. A report that looks like a statement of
account would misrepresent what the product knows.

**Decision.** Every report is an extract over records held in InvoiAI, with a printed coverage block
(considered / included / excluded by reason) and a standing disclaimer. Only recorded values are copied;
rows with missing required fields are excluded and counted, never zero-filled. No cross-currency totals.
Forbidden framing: ledger, general ledger, trial balance, statement of account, P&L, balance sheet, aged
creditor statement, statutory report. Expense reports are owner-scoped because `Expense` has
`owner_type`/`owner_id` and no `org_id`, so an org-wide expense report is not possible without a schema
change.

**Consequences.** Ageing is limited to bills with a recorded `due_date`; `balance_due` is used as
recorded, never estimated. Reports that cannot be computed from available fields are cut, not
approximated. Full contract in `ARCHITECTURE_PROPOSAL.md` §6.1.

**Revisit when** a real ledger or accounting integration is added — at which point reports may be
repositioned against it, not before.

---

## DH-014 — Rendering security boundary is wider than Jinja2

**Status:** P — proposed · 2026-11-23

**Context.** Templates are org-authored HTML. Jinja2's `SandboxedEnvironment` constrains template
expressions only; WeasyPrint afterwards fetches URLs, resolves `file://`, reads local files, imports CSS
and can embed attachments. Upstream docs warn that long renderings, infinite loops and unlimited CSS
values are real, and that "restricting HTML document size is not enough".

**Decision.** Defence in depth, all required:

1. `weasyprint>=70.0` pinned (CVE-2026-55073).
2. Deny-all `url_fetcher` raising `FatalURLFetchingError`; `base_url=None`; never pass caller-influenced
   values to `stylesheets=` or `xmp_metadata=`.
3. HTML/CSS sanitiser at publish **and** at render: tag/attribute allowlist, no `<script>`, `<link>`,
   `<style>`, `<embed>`, `<object>`, `<iframe>`, no `@import`, no remote `url()`, no `rel=attachment`.
4. Post-render assertions: `attachments == []`, no `/EmbeddedFiles`, page count within cap, hash recorded.
5. Preview returns PDF bytes, never rendered HTML from the app origin.
6. Resource caps and a timeout, enforced in a worker with a read-only filesystem, no network and a memory
   limit.
7. Tenant-scoped template lookup, per-render cache (never process-global), plain frozen context objects.

**Consequences.** Org-editable templates are only safe as constrained/locked layouts or sanitised HTML;
that choice is open decision 1. A PDF renderer is now a security-sensitive component, so upgrades go
through the golden-file and hostile-fixture suites.

**Revisit when** a different renderer (Gotenberg/Chromium) is adopted — the SSRF and resource-exhaustion
analysis must be redone for that engine, not inherited.

---

## DH-015 — Issued documents are immutable and append-only at the database level

**Status:** P — proposed · 2026-11-23

**Context.** Service-layer checks are bypassable by a future code path, a direct SQL client or a bug. The
lifecycle promises that an issued document can never silently change.

**Decision.** A `before update` trigger rejects changes to `document_number`, `render_context`,
`source_hash`, file fields, `template_id`/`template_version`, `issued_at` and `source_id` once the row is
`issued`/`voided`/`superseded`, and rejects transitions out of the terminal states. `authenticated` gets no
`DELETE` grant and there is no delete policy; only the organization cascade or an explicitly audited
`app.allow_document_purge` transaction may remove rows. Events are append-only (select + insert policies;
no update/delete). Voiding stores a **separate watermarked artifact** so the frozen original is never
re-rendered.

**Consequences.** A correction is a new document (supersede), never an edit. Retention deletion for issued
documents becomes a deliberate, audited operation rather than a normal code path.

**Revisit when** a legal retention requirement forces deletion — the mechanism exists, the policy does not.

---

## Open questions blocking implementation

| # | Question | Blocks |
|---|---|---|
| 1 | Template customisation: fixed layouts, or org-editable templates? If editable, full HTML/CSS or constrained fields on a locked layout? | Phase 1 scope; DH-014 controls |
| 2 | Approval: must a second person approve before issue, or may the creator issue directly? Is a distinct `documents:approve` permission and segregation of duties required? Is a rejected draft editable or discarded? | Lifecycle, permissions, `status` model |
| 3 | Draft editing: presentation fields only, or re-resolve live records? What happens to an approved draft when the source record changes? | Snapshot semantics |
| 4 | Storage and retention: how long, who may delete, inherit source retention or its own window, and may an issued document ever be deleted rather than voided? | Retention job, DH-012/DH-015 |
| 5 | Navigation: top-level "Documents" area, tab inside existing AP surfaces, or both? Where does creation start? | Frontend routes |
| 6 | System templates: seed per organization (`org_id` not null) or allow global rows (`org_id is null` with a separate read policy)? | RLS statements, seeding migration |
| 7 | Expense reports: owner-scoped only, or dropped from V1 until `Expense` has an org association? | Report scope (DH-013) |
| 8 | Source-record deletion: keep the issued snapshot and mark it orphaned, or refuse the source delete? | Polymorphic source integrity |
| 9 | Sign-off on DH-010 (roadmap scope amendment) | Phase 1 start — Phase 0 only until resolved |

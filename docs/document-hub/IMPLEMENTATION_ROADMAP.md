# Document Hub — Implementation Roadmap

> **Status:** proposal. Nothing has been scheduled, estimated as a commitment, or started.
> Sequencing follows `PRODUCTION_ROADMAP.md` rule 9: derive dates from spike evidence, and treat CI
> results as the only accepted evidence of passing tests.

## 0. Shape of the plan

Four phases. Each phase ends at a gate that either passes with evidence or the next phase does not start.
Phase 0 is deliberately cheap and exists to kill the two assumptions that would otherwise be discovered
halfway through: that WeasyPrint runs inside the real image, and that the staging schema matches the
models.

| Phase | Theme | Outcome | Indicative engineering effort |
|---|---|---|---|
| 0 | Spike and evidence | One real PO PDF rendered from staging data, inside the deployment image | 2–4 days |
| 1 | Registry and PDF core | Company profile, number series, templates, registry, PO + goods receipt rendering, list/preview/download UI | 8–12 days |
| 2 | AP document coverage and reports | Remittance advice, bill cover sheet, AP summary, ageing/spend reports (PDF + XLSX + CSV), approve/issue/void, template management | 8–12 days |
| 3 | Deferred and optional | Letters, expense reports, DOCX, Gotenberg swap if evidence demands it | only if approved |

Effort is engineering-days for one developer familiar with the codebase, excluding design review and
excluding any rework caused by a failed gate. It is not a date.

## Phase 0 — Spike and evidence

Purpose: prove the renderer and the data before writing production code.

1. **Renderer spike, including the security fixtures.** Install **WeasyPrint ≥ 70.0** in a disposable
   environment that mirrors `backend/Dockerfile`, render one A4 purchase order with header, repeated
   table header, page footer "Page X of Y" and an embedded logo. Record: install steps, system packages
   required, render time for 1 page / 5 pages / 50 lines, output size, visual result, resolved version,
   licence notices for the full transitive tree. If it fails, evaluate Gotenberg against the same
   fixtures and record the comparison.

   Then run the hostile fixtures from `ARCHITECTURE_PROPOSAL.md` §9.1 and record the observed behaviour,
   not the intended behaviour: `file:///etc/passwd` in `img`, in CSS `url()` and in an `@import`;
   `http://169.254.169.254/` image; `link rel=attachment`; `a rel=attachment`; enormous CSS page/font
   sizes; `<script>` in the template; 10 000-row table; 50 MB `data:` image. Each must fail closed, within
   the timeout, with no file contents and no `/EmbeddedFiles` in the output.
2. **Schema verification.** Compare `purchase_orders`, `purchase_order_lines`, `goods_receipts`,
   `goods_receipt_lines`, `payment_instructions`, `payment_instruction_events`, `vendors`,
   `organizations`, `organization_settings` against staging. Record every column the adapters need and
   every mismatch with the domain models. (`backend/schema.sql` is a 29-line stub; do not trust it.)
3. **Audit shape check — resolved during review.** `AuditService.log()` is generic (org, actor, action,
   resource, old/new values) and `audit_logs` already has the org/actor/resource/time indexes. Confirm on
   staging, then write the compliance trail to `AuditService` and the UI timeline to
   `issued_document_events` from one helper — not two competing histories.
4. **Template proof.** Hand-write the three V1 layouts (PO, goods receipt, remittance advice) as Jinja2 +
   print CSS against real-looking data. This is the design decision that is cheapest to make now.
5. **Tenant/RLS pattern check.** Confirm the 20261012 policy predicate against staging, then adopt the
   **split** policies in `ARCHITECTURE_PROPOSAL.md` §4.6 rather than copying `for all` onto append-only
   tables: no delete policy on issued documents, select+insert only on events, select only on the series.

**Gate:** a PO PDF and a goods-receipt PDF render from staging data in an environment equivalent to
production, with licences enumerated, render time measured, resolved WeasyPrint version ≥ 70.0, and every
hostile fixture rejected. No product code written yet.

## Phase 1 — Registry, numbering and the first two document kinds

Ordered so each step is independently reviewable.

1. Migration: `organization` document profile columns (legal name, address lines, city, region, postcode,
   country, registration number, document phone/email, footer). Additive, no backfill.
2. Migration: `document_number_series` + `next_document_number(org_id, doc_kind, prefix)`, modelled on
   `20261110_purchase_order_00_org_number.sql`, with the explicit prefix map, `unique (org_id, prefix)`,
   format checks and the same `revoke`/`grant to service_role`. Unit test atomicity with concurrent calls
   and test that two concurrent issues never receive the same number.
3. Migration: `document_templates`, `issued_documents`, `issued_document_events`, split RLS policies,
   indexes, immutability trigger and seed system templates (one per V1 kind). Seeding mechanism depends on
   open decision 6 (per-org vs global rows).
4. `app/services/hub/sources/purchase_order.py` and `.../goods_receipt.py`: read source, build
   `RenderContext`, carry existing amounts, never recompute across modules.
5. `app/services/hub/templates.py` (sandbox, filter/global allowlist, HTML/CSS sanitiser, publish-time
   compile) and `app/services/hub/render.py` (deny-all `url_fetcher`, `base_url=None`, no
   `stylesheets=`/`xmp_metadata=` URLs, output assertions, page count via existing `pypdfium2`).
6. `app/services/hub/registry.py`: create draft, approve, issue (idempotent, number at issue, upload via
   `upload_and_verify`, hash, page count), void, supersede, event emission.
7. `app/routers/document_hub.py` + permission strings + rate limits + fresh-MFA on download.
8. Frontend: `/dashboard/hub`, `/dashboard/hub/new`, `/dashboard/hub/[id]`,
   `/dashboard/settings/company-profile`.
9. Feature flag `features.document_hub`, default off.

**Gate:** an org can fill its profile, create a PO draft, preview it, approve it, issue it, download the
PDF, and see the same number on reload. A second org cannot see any of it. A source PO record is
byte-identical before and after (verified by comparing the row). Issuing twice with the same idempotency
key produces one document and one number. An adversarial template cannot read a local file, reach the
network or attach a file. An issued row cannot be updated or deleted through the API or a direct
`authenticated` SQL call.

## Phase 2 — AP coverage, reports and lifecycle surface

1. Adapters: `payment_instruction` → remittance advice; `document` + `InvoiceCoding` → vendor bill cover
   sheet; aggregate queries → AP summary, ageing, spend.
2. Report path: `ReportContext` → PDF (HTML table), XLSX (existing openpyxl exporter), CSV (existing).
   Reuse `ExportService` rather than a second spreadsheet writer. Every format emits the coverage block
   and disclaimer from §6.1 of the architecture.
3. Worker offload for report renders and large documents; bounded request times.
4. Lifecycle surface: approve/issue/void/supersede actions with reasons, timeline from
   `issued_document_events`, "source updated since generation" warning.
5. Template management: version list, edit, publish with compile **and sanitise** check, PDF preview,
   revert to a system template. Scope depends on open decision 1.
6. Retention controls: draft cleanup job, issued artifacts exempt, void retained with reason.

**Gate:** all V1 `doc_kind` values render from real records; a voided document keeps its number and serves
its **separately stored watermarked copy** while the original hash is unchanged; an edited template
creates a new version and cannot alter a previously issued PDF (hash comparison test); reports larger
than 200 rows complete through the worker without timing out the API; every report prints its coverage
block and disclaimer, and the fixture with 40% missing due dates reports the exclusions instead of
treating them as zero.

## Phase 3 — Only if separately approved

- Internal letterhead documents (`letter`), expense reports (`expense_report`).
- DOCX output. Requires a licence decision first (see `OPEN_SOURCE_RESEARCH.md` §3) — do not start before
  that review.
- Replacing WeasyPrint with Gotenberg **only** with recorded evidence of a fidelity or throughput failure.
- Email delivery of documents, batch scheduling, per-customer branding beyond one template set.

## Test plan (mapped to the gates)

| Area | Test | Where |
|---|---|---|
| Numbering | Concurrent `next_document_number` calls never collide; sequence is `PREFIX-000001`; voided numbers are not reissued | SQL/pytest |
| Immutability | Issued PDF `sha256` unchanged after template edit and after source-record edit | pytest |
| Snapshot fidelity | `render_context` equals the values the PDF was rendered from; totals copied, not recomputed | pytest |
| Sandboxing | Template attempting `__class__` traversal, `{% include %}`/`{% extends %}` outside the allowlist, the `safe` filter, or an unknown filter fails publish/render | pytest |
| SSRF / local file | `file://` in `img`, CSS `url()`, `@import`, and `http://169.254.169.254/` all fail closed; output contains no file canary and no `/EmbeddedFiles` | pytest + fixture PDFs |
| Attachment channel | `link rel=attachment` / `a rel=attachment` sanitised; `document.metadata.attachments == []` asserted before write | pytest |
| Preview safety | `/preview` responds with `application/pdf`, never `text/html`; no rendered template HTML reachable from the app origin | pytest |
| Resource caps | Oversized HTML, huge CSS page size, 10 000 rows and a 50 MB data URI each terminate within the configured timeout, not the request timeout | pytest (marked slow) |
| Report honesty | Fixture with 40% null `due_date` prints `included/excluded(missing_due_date)` and does not total excluded rows; no cross-currency total | pytest |
| Number never reused | After a rolled-back issue, the next issue skips the allocated number and never reuses it; after a process restart the series continues | SQL/pytest |
| Tenant isolation | Cross-org read/issue/download returns 404; RLS blocks direct table access | pytest + staging |
| Idempotency | Duplicate `issue` with the same key → one row, one number, one object; two concurrent issues of the same key → one succeeds, one returns the existing row | pytest |
| Immutability at DB | Direct `update` of `render_context`/`document_number` on an issued row raises `ISSUED_DOCUMENT_IMMUTABLE`; `delete` is denied | SQL |
| Storage | Generated object exists and is verified after upload; signed URL TTL ≤ 300 s | existing storage test pattern |
| Permissions | `documents:view` cannot issue; fresh MFA required on download | pytest |
| Rendering | Fixture snapshots: 1 page, multi-page with repeated headers, long description wrapping, missing optional fields | golden-file comparison |
| Regression | Existing upload/OCR/export/AP suites still pass | CI |

Practical note: local test collection has previously been unreliable (missing `slowapi`,
`pytest-asyncio` registration, slow filesystem imports on Windows). The gate is CI, not a local run.

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| WeasyPrint system libraries missing in the deployed image | Medium | Phase 0 spike on the real image; failure surfaces as a clear 503, not an API crash |
| Print CSS fidelity below expectation (complex grids) | Medium | Layouts designed for print; Gotenberg fallback documented with a trigger |
| Roadmap conflict: "shared document generator beyond invoice PDF" is marked deferred | **Certain** | Recorded as an explicit scope amendment in `DECISIONS.md`; needs product-owner sign-off before Phase 1 |
| Snapshot drift (source updated after issue) | High over time | Visible "source updated since generation" state; replaced by supersede, never silent re-render |
| Template sandbox escape / SSRF / local file read | Low likelihood, severe impact | Jinja2 sandbox **plus** deny-all `url_fetcher`, HTML/CSS sanitiser, pinned WeasyPrint ≥ 70.0, worker with no network and read-only FS (§9.1). Tested with hostile fixtures, not assumed |
| WeasyPrint advisory or breaking layout change on upgrade | Medium over time | Version pinned; upgrade only with the golden-file render suite and a re-read of the security advisories |
| Reports read as a ledger | Medium | Coverage block, standing disclaimer, forbidden framing list, and a Phase 2 gate test |
| Number gaps or duplicates under concurrency | Low | Atomic upsert function reused from the PO implementation; uniqueness index |
| Scope creep into AR/sales invoices | Medium | V1 kind list fixed in `ARCHITECTURE_PROPOSAL.md` §6; new kinds need a decision entry |
| Two competing document mental models (`documents` inbox vs registry) | Medium | Clear naming in UI: "Documents" = received, "Document Hub" = issued; no shared status column |

## What this roadmap does not do

It does not schedule a launch date, change `PRODUCTION_ROADMAP.md`, add a dependency, alter the `documents`
table, touch auth, or commit anything. Approval of `ARCHITECTURE_PROPOSAL.md` and `DECISIONS.md` is the
precondition for Phase 0.

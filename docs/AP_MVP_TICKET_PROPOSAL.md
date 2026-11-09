# InvoiAI AP MVP — Revised Ticket Proposal

> **Status:** Proposal only. **Not published.** No ticket has been created in a tracker.
> **Date:** 2026-11-08 (supersedes the 2026-11-07 draft)
> **Source of truth:** `docs/PRODUCTION_ROADMAP.md` (including the 2026-11-07 Sage amendment and the 2026-11-08 signup, team-pricing, and frontend-direction amendment) and the reconciled `docs/AP_MVP_IMPLEMENTATION_SPEC.md`.
> **Change from the earlier draft:** Sage work is retained, not removed. Sage is retargeted from a product-family selection to a fixed Sage Accounting AP scope. Four user-visible slices are added: AP roles and seat usage, pricing/trial/billing, the design foundation, and the public landing/pricing journey. The former tickets 11–29 shift to 15–33.

## Why there are 33 tickets

The earlier draft had 29 tickets. The product-owner direction adds four reviewable slices and keeps signup and onboarding separate:

- **Ticket 7 stays registration only.** It collects first name, surname, business email, and password or Google, with an optional mobile number. Keeping it small is the point.
- **Ticket 10 stays business onboarding.** It becomes the resumable wizard and creates the first workspace. Splitting registration from onboarding avoids one long form.
- **Ticket 11 is new: AP roles, invitations, approver assignment, and seat usage.** These are user-visible and span auth, organization membership, and billing. They cannot be hidden inside onboarding or billing without becoming untestable.
- **Ticket 12 is new: pricing, trial, invoice allowance, and GBP/USD billing.** Plan catalog, trial, seats, allowance, checkout, and the billing surface form one coherent slice with its own acceptance criteria.
- **Ticket 13 is new: design foundation and product UI system.** Token consolidation, glass/contrast rules, motion, and Lottie policy must land before new product surfaces are styled ad hoc.
- **Ticket 14 is new: public landing and pricing journey.** It is public-only, depends on the live catalog from ticket 12 and the tokens from ticket 13, and keeps Scroll Craft storytelling out of the authenticated app.
- **Old tickets 11–29 shift to 15–33.** Their scope is preserved except for cross-references, the removal of the permanent Free plan, and the trial/seat wording.

The earlier fixes remain:

- **Import seams versus provider imports.** Tickets 19–21 build the manual path and the provider-neutral seam; the real imports are proven inside each provider slice (26–29). This fixes the dependency order without adding a ticket.
- **The Sage slice stays split.** Ticket 28 covers authorization, business selection, and reference-data reads; ticket 29 covers Purchase Transactions write-back, retry/duplicate, and boundary enforcement.

No Sage work is removed: Sage trial-business evidence, duplicate prevention, retry reconciliation, and the excluded-resource test remain explicit acceptance criteria. Sage Business Cloud Accounting API has no development sandbox, so Sage evidence comes from **API 3.1 against a Sage trial business account**. Xero and QuickBooks Online keep their sandbox evidence.

## At a glance

| # | Ticket | Blocked by |
|---|---|---|
| 1 | Sage AP capability verification and ADR | None |
| 2 | Provider contract test harness and provider evidence template | 3 |
| 3 | Canonical migration chain and reproducible CI | None |
| 4 | Tenant isolation, RLS, and audit indexes | 3 |
| 5 | Private storage, quarantine, attachment scanning, and restore | 3 |
| 6 | Observability, alerts, and operator runbooks | 3, 4 |
| 7 | Account registration, six-digit email OTP, and server-side verification gate | 3 |
| 8 | Google sign-in, sessions, and password recovery | 7 |
| 9 | Administrator MFA and step-up | 7 |
| 10 | Resumable business onboarding, workspace creation, market currency, and cache isolation | 7, 8 |
| 11 | AP roles, invitations, approver assignment, and seat usage | 4, 10 |
| 12 | Pricing, trial, invoice allowance, seats, and GBP/USD billing | 10, 11 |
| 13 | Design foundation, tokens, and product UI system | None |
| 14 | Public landing and pricing journey | 12, 13 |
| 15 | Upload intake and processing timeline | 5, 7 |
| 16 | Forwarding-email intake with quarantine and scanning | 5, 15 |
| 17 | Extraction evidence, deterministic validation, and duplicate review | 15, 16 |
| 18 | Single document review surface | 17 |
| 19 | Vendors and provider-neutral supplier import seam | 4, 7 |
| 20 | Chart of accounts, GL coding, and provider-neutral COA import seam | 19 |
| 21 | Purchase orders, goods receipts, and CSV import | 19 |
| 22 | Two-way and three-way matching with line allocation and tolerances | 20, 21 |
| 23 | Approval workflow, limits, separation of duties, and reapproval | 22 |
| 24 | Provider connection lifecycle and organization selection (Xero and QuickBooks Online) | 4, 6, 23 |
| 25 | Provider-neutral approved-bill write-back foundation | 24 |
| 26 | Xero vertical slice | 2, 19, 20, 23, 25 |
| 27 | QuickBooks Online vertical slice | 2, 19, 20, 23, 25 |
| 28 | Sage connection, business selection, and reference-data reads | 1, 2, 19, 20, 24 |
| 29 | Sage Purchase Transactions write-back and boundary enforcement | 2, 25, 28 |
| 30 | Cross-provider duplicate, retry, and currency verification | 26, 27, 29 |
| 31 | Payment instruction CSV/PDF export and customer-reported status | 23 |
| 32 | AP dashboard, search, quota behavior, billing surface, and cleanup | 18, 23, 31 |
| 33 | Launch hardening and pilot readiness | 5, 6, 30, 31, 32 |

### Suggested first wave

- Start **1** (Sage verification), **3** (migration/CI), and **13** (design foundation) immediately.
- After 3: **2**, **4**, **5**, and **7** can proceed in parallel.
- After 7 and 8: **10**. After 10: **11**. After 10 and 11: **12**. After 12 and 13: **14**.
- After 4 and 7: **19** can start; after 5 and 7: **15**.
- Do not start **28** before ticket 1 records the Sage ADR; do not start **29** before **28** and **25** are done.
- Do not publish final GBP/USD prices, invoice allowances, additional-seat rates, or proration from ticket 12 or 14 until the product owner approves them. The seat structure and trial terms are already approved.

---

## Foundation and gates

### 1. Sage AP capability verification and ADR

**What it delivers:** The team has verified, from official Sage documentation and a **Sage trial business account on API 3.1**, exactly how the agreed Sage Accounting AP resource areas behave. The result is a short ADR and an evidence record that the rest of the Sage work can rely on.

**Blocked by:** None.

- [ ] The target is confirmed as **Sage Business Cloud Accounting API 3.1**. The ADR records that Sage has **no development sandbox**, so all read/write evidence comes from a Sage trial business account. Sage Active, Sage 50, Sage 100, and Sage Intacct are not substitutes.
- [ ] The exact Sage Accounting product, edition/version, supported UK/US regions, and regional base URL/token endpoints are recorded from official documentation.
- [ ] The ADR states whether “Sage Accounting Start (Quotes & Invoicing Only)” supports supplier purchase transactions, or is not AP-compatible.
- [ ] The authorization flow, redirect rules, token lifetime/refresh, scopes, and business-selection mechanism are recorded. Resource-area names are not treated as scopes.
- [ ] The **User Accounts** response and the way to list businesses the authorized user can access are proven in the Sage trial business account.
- [ ] **Contacts**, **Chart of Accounts**, **Status Codes & Types**, **Currencies**, **Taxes**, and relevant **Settings** read shapes are captured with sample responses from the trial business.
- [ ] **Purchase Transactions** create/read/update is proven for one supplier invoice in the trial business; relevant credit-note behavior is proven or explicitly marked unavailable.
- [ ] Currency results for GBP, USD, and NGN are recorded as supported, rate-required, or unsupported.
- [ ] The optional **Attachments** capability is checked and a first-slice include/exclude decision is recorded.
- [ ] The excluded areas are listed explicitly: Banking, Payments & Receipts, bank accounts, journals/ledger, Sales Transactions, Opening Balances, Products & Services, Reporting.
- [ ] The ADR records the evidence, limitations, and any app-review or partner-approval requirement. No production code is shipped in this ticket.

### 2. Provider contract test harness and provider evidence template

**What it delivers:** One behavioral test suite can exercise Xero, QuickBooks Online, and Sage with fake transports, so duplicate creation, retry, organization headers, currency gates, and excluded-resource calls are checked the same way for every provider.

**Blocked by:** 3.

- [ ] The harness runs in CI and can register a fake transport per provider.
- [ ] It asserts no provider call before approval, exactly one create call on the first attempt, adoption of an existing record after a timeout, retry after 5xx, stop after 4xx, and backoff after 429.
- [ ] It asserts the correct organization/tenant/realm/business header per provider without assuming an unverified header name for Sage.
- [ ] It asserts that a provider without PO support fails with a typed unsupported error instead of calling an endpoint.
- [ ] It includes a negative assertion that Sage never calls an excluded resource.
- [ ] A provider evidence template records provider, environment (Xero/QuickBooks sandbox or Sage trial business), API version, test date, operator, resource coverage, currency results, retry result, and duplicate result.

### 3. Canonical migration chain and reproducible CI

**What it delivers:** A new developer or CI runner can install, migrate, and run the full suite from a clean checkout, and the migration path matches staging.

**Blocked by:** None.

- [ ] One canonical migration path is declared and the manifest text that points elsewhere is corrected.
- [ ] Missing test dependencies and async configuration are fixed; the suite collects with no errors.
- [ ] The runtime and dependencies are pinned; CI reproduces the local result.
- [ ] A staging-versus-migration comparison check exists and reports drift.
- [ ] No feature ticket may use an unpinned local test run as acceptance evidence.

### 4. Tenant isolation, RLS, and audit indexes

**What it delivers:** A second tenant cannot read, list, search, download, export, or process the first tenant's records through any API or worker path.

**Blocked by:** 3.

- [ ] RLS is enabled on tenant-owned tables used by the AP workflow.
- [ ] Policies use active membership; service-role access remains limited to workers.
- [ ] Two-user/two-organization tests cover list, detail, search, export, download, document storage, and background jobs.
- [ ] Workers derive the organization from the record, not from a job payload.
- [ ] Audit indexes support querying by organization, actor, resource, event, and time.
- [ ] Cross-tenant attempts return a safe denial without leaking record existence.

### 5. Private storage, quarantine, attachment scanning, and restore

**What it delivers:** Uploaded and emailed invoices are stored privately, suspicious files are quarantined, and a backup can be restored and verified.

**Blocked by:** 3.

- [ ] Files are validated by content, not just extension; oversized and spoofed files are rejected.
- [ ] Private storage uses short-lived signed downloads; no public bucket or permanent URL exists.
- [ ] Malware-positive and policy-failed attachments enter quarantine and do not reach OCR.
- [ ] A backup restore is performed and the restored records are verified.
- [ ] Retention/deletion hooks do not delete records needed by an open approval or audit trail.

### 6. Observability, alerts, and operator runbooks

**What it delivers:** Operators can see queue age, extraction failures, provider sync failures by provider, webhook lag, notification delivery, trial/seat/allowance state, and quota state, and they have a runbook for each failure.

**Blocked by:** 3, 4.

- [ ] Metrics and structured logs cover API latency/errors, queue age, OCR/extraction failures, provider sync by provider, webhook lag, notifications, plan usage, seat usage, trial state, and allowance usage.
- [ ] Alerts have a named owner and a runbook.
- [ ] Runbooks cover stuck workers, provider outage, webhook replay, restore, customer-data deletion, and secret rotation.
- [ ] A test alert is delivered end to end.
- [ ] Logs never contain tokens, OTPs, raw documents, or provider payloads.

---

## Identity and onboarding

### 7. Account registration, six-digit email OTP, and server-side verification gate

**What it delivers:** A new user can register with first name, surname, business email, and password (or Google), verify with a six-digit email code, and reach the workspace only after verification. Mobile is optional and never blocks signup.

**Blocked by:** 3.

- [ ] Registration collects and validates first name, surname, business email, and password. Mobile with country code is optional.
- [ ] No company registration number, tax ID, or payment card is requested.
- [ ] The OTP screen supports paste, auto-advance, expiry countdown, resend cooldown, attempt limits, and locked/expired recovery.
- [ ] Codes are hashed, single-use, and never logged or stored client-side.
- [ ] Unverified users receive a server-side denial on dashboard, documents, AP, approvals, integrations, and exports.
- [ ] Resend and verification are rate-limited and non-enumerating.
- [ ] Email OTP works with no SMS dependency; a user in Nigeria or anywhere SMS is unavailable can finish signup.
- [ ] Signup, verification, and denial paths have backend and frontend tests.
- [ ] The current link-based verification screen is replaced or clearly reduced to a migration alias.

### 8. Google sign-in, sessions, and password recovery

**What it delivers:** A user can sign in with Google, maintain a safe session, log out, and recover a password without account enumeration.

**Blocked by:** 7.

- [ ] Google uses the server-side authorization-code flow with state and nonce; provider tokens never reach browser storage.
- [ ] An existing account is linked only when the provider email is verified; no silent merge occurs.
- [ ] Login, logout, refresh, forgot-password, and reset-password work end to end.
- [ ] Sessions rotate on refresh and are revoked on logout, password change, and membership removal.
- [ ] Cancelled or denied Google consent is handled as a normal user outcome.

### 9. Administrator MFA and step-up

**What it delivers:** Owners and administrators must use TOTP MFA, and sensitive actions require a fresh step-up challenge.

**Blocked by:** 7.

- [ ] TOTP enrollment and verification work, with ten single-use recovery codes shown once.
- [ ] An owner/admin without a factor is restricted to MFA setup, logout, and support.
- [ ] Step-up is enforced server-side for organization settings, role changes, provider connect/reconnect/switch, seat changes, exports, and future bank-detail actions.
- [ ] Recovery codes are hashed and single-use; regeneration requires step-up.
- [ ] MFA is separate from email verification and cannot be bypassed by the frontend.

### 10. Resumable business onboarding, workspace creation, market currency, and cache isolation

**What it delivers:** A verified user completes a short, resumable onboarding wizard, gets a workspace with the creator as owner, and sees the correct default currency by market. The wizard can be left and resumed without losing answers.

**Blocked by:** 7, 8.

- [ ] Onboarding saves a draft after each step and resumes on the same step.
- [ ] It collects business/workspace name, country, currency with override, business type/registration status (including “not yet registered”), industry, team size, monthly invoice volume, and accounting software.
- [ ] “No accounting software” and “not sure” are accepted and lead to manual AP.
- [ ] UK defaults to GBP, US defaults to USD, Nigeria may suggest NGN, and the currency remains editable.
- [ ] The Sage choice explains that the supported product/edition is verified during connection setup; no quotes-only edition is promised as AP-compatible.
- [ ] Optional teammate invitations and approver assignment are offered, with seat impact previewed and deferred to ticket 11 enforcement.
- [ ] Referral-code collection is omitted unless an existing launch purpose is confirmed; it is not part of the default flow.
- [ ] Company registration number and tax ID are not requested.
- [ ] The first workspace, owner membership, settings, and usage row are created atomically; completion is idempotent.
- [ ] Logout and workspace switch clear organization-scoped business data; a second member sees only the active workspace.
- [ ] Cross-tenant workspace access is denied.

**Implementation gate:** The current `OrganizationService.create_workspace` bootstraps the organization, owner membership, settings, and usage through separate Supabase requests and compensates by deleting the organization if setup fails. This is not a database transaction. Do not mark the atomic-creation acceptance item complete until a transaction-backed database RPC is designed against the deployed core schema and verified; that schema is not fully represented in this checkout.

---

## Team, pricing, and billing

### 11. AP roles, invitations, approver assignment, and seat usage

**What it delivers:** A workspace owner can invite a Workspace Admin, Invoice Reviewer, or Approver, assign an approver during onboarding or later, and see exactly how many seats are included, used, and pending. Each unique active member counts once.

**Blocked by:** 4, 10.

- [ ] The invite UI exposes the three AP roles — **Workspace Admin**, **Invoice Reviewer**, **Approver** — plus owner where appropriate, mapped to the existing permission set.
- [ ] The owner can invite by email, resend or cancel an invitation, change a role, and remove access.
- [ ] An approver can be assigned during onboarding or later.
- [ ] Seat usage counts each unique active membership once; a member with several roles still counts once.
- [ ] Pending invitations, revoked invitations, removed members, and disabled members do not consume a seat.
- [ ] `GET /api/v2/billing/seats` (or equivalent) returns included, used, pending, available, and the plan's additional-seat rate.
- [ ] An invitation that would exceed the seat limit is blocked server-side with `SEAT_LIMIT_REACHED`; the UI explains “add seats or remove access.”
- [ ] Changing a role never changes the seat count.
- [ ] Removing a member releases the seat immediately; the last-owner rule still applies.
- [ ] The onboarding invite step previews seat impact before sending.
- [ ] Downgrading below the active member count keeps existing members but blocks new invitations until the count fits or seats are added.
- [ ] Tests cover multi-role member, pending invitation, removal, limit, downgrade, and cross-tenant denial.
- [ ] The seat-usage endpoint is the single source ticket 12 uses for add-on pricing and next-charge estimates.

### 12. Pricing, trial, invoice allowance, seats, and GBP/USD billing

**What it delivers:** The workspace has an approved plan catalog, a time-limited trial, a monthly invoice allowance separate from seats, correct GBP/USD checkout, and a billing surface that shows plan, trial, allowance, seats, and next charge. There is no permanent free plan.

**Blocked by:** 10, 11.

**Approval gate:** The **Solo/Duo/Team seat structure** (1/2/5 active seats plus paid additional seats) and the **14-day, 25-invoice, no-card trial with read-only plus export at the end** are approved. Still require product-owner approval: **final GBP/USD prices, monthly invoice allowances, additional-seat rate, and proration**. This ticket builds the catalog shape, configuration, and UI; it must not hardcode invented values. If those amounts are missing, keep paid checkout gated off.

- [ ] The plan catalog stores name, GBP price, USD price, monthly invoice allowance, included seats, additional-seat rate, and feature list.
- [ ] The approved structure is represented: **Solo** (1 seat), **Duo** (2 seats), **Team** (5 seats), plus paid additional seats.
- [ ] No FREE plan or Free price ID exists; the public catalog exposes a trial, not a permanent free tier.
- [ ] Trial configuration uses the approved values: 14 days, 25 processed invoices, no card at signup, read-only plus export at the end.
- [ ] Stripe checkout sends the correct currency price and the seat quantity; it does not hardcode `quantity: 1`.
- [ ] A trial starts without a card; one trial per workspace.
- [ ] The invoice allowance counts documents entering the AP pipeline only. Approvals, exports, sync attempts, and supplier-payment instructions do not consume it.
- [ ] At 80% and 100%, show a persistent warning; at the cap, pause only new AI/OCR extraction. Manual work, review, approval, sync, export, and existing records continue.
- [ ] At trial end without a plan, the workspace becomes read-only plus export; a banner shows days left, invoices used, and the exact end behavior.
- [ ] The billing page shows current plan, trial state, invoice allowance meter, seat meter, next charge, currency, invoices, payment method/portal, and cancel/renew.
- [ ] UK workspaces display GBP and US workspaces display USD; no silent currency fallback.
- [ ] Nigeria billing eligibility is surfaced as a separate item and never blocks AP.
- [ ] Supplier-payment count never affects billing.
- [ ] Tests cover trial start/end, cap pause, seat quantity, GBP/USD selection, no free plan, and allowance separation.

---

## Design and public surface

### 13. Design foundation, tokens, and product UI system

**What it delivers:** The product has one semantic token layer and a small set of premium, accessible primitives: restrained glass, glossy accents, a few dimensional moments, purposeful motion, and a clear Lottie policy. The direction applies to the authenticated product and must not reduce contrast on financial work.

**Blocked by:** None. Land before ticket 14 and before new product surfaces are styled ad hoc.

- [ ] Consolidate the competing `:root` blocks in `frontend/src/app/globals.css` into one semantic token layer: surface, ink, muted, accent, border, danger, focus, radius, elevation, and motion.
- [ ] Keep the implemented DM Sans (UI) and Playfair Display (display) pairing; add no new font without a design review.
- [ ] Define glass/gloss/dimensional primitives and their contrast limits; never place blur behind dense text, table values, forms, review, or approval content.
- [ ] Define purposeful transitions of roughly 150–250 ms and a reduced-motion fallback.
- [ ] Define the Lottie policy: meaningful onboarding, success, or empty states only; local, licensed, lazy-loaded; remove or replace remote iframes.
- [ ] Apply the patterns to at least one representative product screen and document the table/form/review/approval rules.
- [ ] Check keyboard focus, contrast, screen-reader status text, mobile layout, and reduced motion.
- [ ] Add no 3D or animation dependency without a specific need; reuse Next.js, Tailwind, Radix, Lucide, React Query, React Hook Form, and Zod.
- [ ] Add visual checks or screenshots for light, dark, reduced-motion, and mobile states.

### 14. Public landing and pricing journey

**What it delivers:** A public landing/pricing page driven by the live catalog, showing approved Solo/Duo/Team plans in GBP or USD, a trial call to action, and no permanent free plan. Scroll Craft storytelling lives here only.

**Blocked by:** 12, 13.

- [ ] Pricing reads the live plan catalog; no hardcoded USD prices, no “Free” card, and no “Start free” claim.
- [ ] Approved plan names, prices, invoice allowances, included seats, and the additional-seat note are shown for the visitor's currency/region.
- [ ] The trial CTA states duration, invoice cap, card requirement, and end behavior from approved values.
- [ ] Scroll Craft storytelling, dimensional moments, and glass/gloss accents appear only on public pages; no scroll hijack or heavy animation enters the app.
- [ ] Hero and pricing remain readable and fast; protect LCP/CLS and do not hide the CTA behind motion.
- [ ] Keyboard access, screen-reader labels, reduced motion, and mobile layouts work.
- [ ] Metadata and copy mention Xero, QuickBooks Online, Sage Accounting, and the no-accounting-software path accurately.
- [ ] Tests or screenshots cover UK GBP and US USD display.

---

## Intake and review

### 15. Upload intake and processing timeline

**What it delivers:** An AP clerk can upload one or many invoices and follow each file from upload through processing, duplicate review, or retry.

**Blocked by:** 5, 7.

- [ ] PDF and image uploads are accepted; unsupported, oversized, and spoofed files show a clear per-file error.
- [ ] Batch upload returns per-file success/failure and does not fail the whole batch for one bad file.
- [ ] The original file is immutable and stored privately with a content hash.
- [ ] Duplicate hashes create a reviewable prompt, not a silent delete or overwrite.
- [ ] The timeline shows queued, reading, extracting, needs review, failed, and retry.
- [ ] Failed processing can be retried without re-upload.

### 16. Forwarding-email intake with quarantine and scanning

**What it delivers:** A supplier can email an invoice to a per-organization address and it becomes the same document type as an upload, with spoofed or unsafe mail quarantined.

**Blocked by:** 5, 15.

- [ ] One forwarding address exists per organization, can be rotated by an administrator, and is shown in the UI.
- [ ] The inbound webhook verifies signature, timestamp, recipient, and replay window.
- [ ] SPF, DKIM, and DMARC failures quarantine the message and attachments for human review instead of silent acceptance or rejection.
- [ ] Attachments pass the same type, size, hash, storage, and duplicate checks as uploads.
- [ ] Repeated webhook delivery and cross-channel duplicates do not create duplicate documents.
- [ ] Sender, attachment-count, message-size, and organization rate limits are enforced.

### 17. Extraction evidence, deterministic validation, and duplicate review

**What it delivers:** A reviewer sees header and line values with confidence and source evidence, deterministic validation results, and a duplicate queue that never silently deletes an invoice.

**Blocked by:** 15, 16.

- [ ] Header and line items are extracted with confidence and raw evidence.
- [ ] Arithmetic, date, due-date, currency, supplier, and duplicate checks produce pass/warning/blocking outcomes.
- [ ] Duplicate candidates explain the match reasons and work across upload and email.
- [ ] A suspected duplicate enters `duplicate review`; it is never auto-deleted or auto-rejected.
- [ ] Corrections preserve the original extraction and record actor, prior value, new value, and timestamp.
- [ ] Money uses fixed-precision decimals; NGN and other non-GBP/USD amounts are preserved exactly.

### 18. Single document review surface

**What it delivers:** A reviewer can compare the source with extracted values, correct header and lines, resolve validation and duplicate prompts, and continue to coding on one surface.

**Blocked by:** 17.

- [ ] The source, header, lines, confidence, validation summary, duplicate prompts, and vendor match are visible together.
- [ ] There is one editing surface; the AP-processing page does not compete with a second document editor.
- [ ] Save and continue persists corrections and recalculates totals.
- [ ] Loading, empty, error, and processing states are explicit.
- [ ] The surface is keyboard usable, labelled, responsive, and respects reduced motion.
- [ ] The surface follows the high-contrast table/form rules from ticket 13; no glass sits behind values.

---

## AP core

### 19. Vendors and provider-neutral supplier import seam

**What it delivers:** An AP clerk can create, edit, and link suppliers with no accounting connection, and the supplier-import path is provider-neutral so each provider slice can prove its own import without changing the workflow.

**Blocked by:** 4, 7.

- [ ] Manual vendor create/edit/search works without any accounting connection.
- [ ] Supplier import is dispatched from the active provider connection, never from the first connection row or a default provider.
- [ ] The import is idempotent and maps by external ID first, then normalized supplier name; a re-run creates no duplicates.
- [ ] Sage supplier mapping is limited to **Contacts** fields needed for matching; unnecessary personal and bank details are never requested or stored.
- [ ] An unknown extracted supplier must be linked or created before bill sync.
- [ ] Creating a supplier in the accounting system is an explicit, audited action, never a silent side effect.
- [ ] The UI shows counts, last sync, and per-resource errors.
- [ ] Real Xero, QuickBooks, and Sage supplier imports are proven in tickets 26–28, not asserted here.

### 20. Chart of accounts, GL coding, and provider-neutral COA import seam

**What it delivers:** An AP clerk can code invoice lines against a seeded manual chart or a chart imported from the connected provider.

**Blocked by:** 19.

- [ ] COA import dispatch is provider-neutral and idempotent; a re-run does not duplicate accounts.
- [ ] Only active, postable accounts are selectable.
- [ ] A starter COA seed works with no provider connected.
- [ ] Rule precedence is exact vendor rule, description/SKU pattern, history, then AI suggestion.
- [ ] Every suggestion states its source and a short explanation.
- [ ] A human approves line coding; a line without an active account is a blocking exception.
- [ ] A coding change after approval revokes approval.
- [ ] Real Xero, QuickBooks, and Sage COA imports are proven in tickets 26–28.

### 21. Purchase orders, goods receipts, and CSV import

**What it delivers:** An AP clerk can match invoices against manual/CSV POs or provider POs where that provider supports them, and record partial goods receipts in InvoiAI.

**Blocked by:** 19.

- [ ] Manual PO creation and CSV PO import work with no provider connected.
- [ ] PO import dispatch uses the active provider connection; no provider is assumed.
- [ ] Xero PO import is proven in ticket 26 and remains Xero's source of truth.
- [ ] QuickBooks PO import is proven or explicitly marked unavailable in ticket 27; it is not claimed without evidence.
- [ ] Sage has no PO sync in the agreed AP scope; ticket 28 records the limitation and manual/CSV POs work.
- [ ] Goods receipts can be entered manually or by CSV and accumulate partially against PO lines.
- [ ] An allocated receipt cannot be silently edited; void requires a reason and audit event.
- [ ] A PO change after allocation flags the match for review without rewriting the allocation.

### 22. Two-way and three-way matching with line allocation and tolerances

**What it delivers:** An invoice can be matched to zero, one, or many POs and receipts, with line-level partial allocation and configurable tolerances.

**Blocked by:** 20, 21.

- [ ] Two-way and three-way matching modes work with partial invoices and partial deliveries.
- [ ] An invoice may reference zero, one, or many POs/receipts.
- [ ] Line-level allocations persist, prevent over-allocation, and show remaining quantity and amount.
- [ ] Price, quantity, and tax tolerances are configurable per organization and per transaction.
- [ ] A mismatch or missing PO/receipt blocks approval unless an authorized approver waives it with a reason and audit event.
- [ ] A successful match never auto-approves.
- [ ] A PO change after allocation flags the match without silently rewriting it.

### 23. Approval workflow, limits, separation of duties, and reapproval

**What it delivers:** An approver sees a clear queue, decisions respect authority and limits, and a critical change after approval forces a new approval.

**Blocked by:** 22.

- [ ] The approval queue shows amount, supplier, due date, coding, matching result, exceptions, and authority context.
- [ ] Approve, request changes, and reject require a reason where the workflow requires one.
- [ ] Limits are enforced in workspace currency; foreign-currency invoices use the invoice-date rate for comparison only and are flagged for FX review.
- [ ] The submitter cannot approve above the configured self-approval threshold; owner/admin self-approval below it is audited.
- [ ] A change to supplier, invoice number/date, currency, total, tax, line amount, GL coding, or allocation revokes approval.
- [ ] Match and coding exceptions block approval unless validly waived.
- [ ] Delegations expire and overdue steps escalate.
- [ ] Approval works with no accounting connection.
- [ ] Every decision records actor, time, amount, currency, authority, and reason.

---

## Accounting providers

### 24. Provider connection lifecycle and organization selection (Xero and QuickBooks Online)

**What it delivers:** An administrator can connect Xero or QuickBooks Online, choose the correct organization explicitly, see status, reconnect, disconnect, and safely switch. The same provider-neutral contract and Sage card are in place, with Sage authorization completed in ticket 28.

**Blocked by:** 4, 6, 23.

- [ ] The integrations page lists Xero, QuickBooks Online, and Sage as required MVP choices; the Sage card shows a capability-verification state with no working-looking connect action until ticket 28 lands.
- [ ] The OAuth callback never auto-selects the first organization, tenant, or realm.
- [ ] Xero shows authorized tenants and QuickBooks shows the authorized company.
- [ ] The administrator confirms exactly one organization; its external ID, name, and region are stored.
- [ ] At most one active accounting connection exists per workspace; connecting another requires an explicit switch.
- [ ] Reconnect updates the same row; disconnect keeps local documents, approvals, exports, and audit history.
- [ ] Switching organization or provider requires confirmation, MFA step-up, and a check for in-flight or approved-but-unsynced bills.
- [ ] Tokens remain encrypted and are never returned to the client or logged.
- [ ] The provider-neutral adapter interface is extended so Sage can register without changing the worker contract.
- [ ] The connection screen shows the supported product/edition when a provider has edition-dependent capabilities.

### 25. Provider-neutral approved-bill write-back foundation

**What it delivers:** An approved invoice is claimed once, checked, created in the selected provider, verified, and either marked synced or left visibly retryable, without duplicate bills.

**Blocked by:** 24.

- [ ] The provider factory returns Xero, QuickBooks, and Sage adapters; it raises a typed configuration error only when credentials or selection are missing.
- [ ] `BillSyncWorker` resolves the adapter from the active connection and does not hardcode QuickBooks.
- [ ] The worker verifies approval, AP-enabled state, no existing provider bill ID, approved coding, linked supplier, and currency policy before any POST.
- [ ] A deterministic `erp_sync_key` and unique constraint prevent independent duplicate syncs.
- [ ] A pre-flight lookup adopts exactly one existing bill; zero creates; more than one or a mismatched match stops with an ambiguity error.
- [ ] A timeout after create reconciles before retry.
- [ ] Currency returns supported, rate-required, or unsupported before any POST; the invoice's stored amount and currency never change.
- [ ] Failure rolls back to a visible approved state with a safe error code and retry action.
- [ ] The manual no-connection path never invokes the worker and remains fully usable.

### 26. Xero vertical slice

**What it delivers:** An administrator connects a chosen Xero tenant, imports suppliers/accounts/POs, and an approved invoice becomes one correct `ACCPAY` bill in a Xero sandbox.

**Blocked by:** 2, 19, 20, 23, 25.

- [ ] The selected Xero tenant header is correct on every request.
- [ ] Supplier, COA, and PO imports are idempotent and map by external IDs.
- [ ] An approved invoice creates one `ACCPAY` bill with the original supplier, number, dates, currency, lines, tax references, and account codes.
- [ ] No bill is created before approval and authorization checks.
- [ ] A timeout reconciles to the existing bill; a retry cannot create a second one.
- [ ] 5xx retries, 4xx stops with a field-level reason, 429 backs off, and 401/403 prompts reconnect.
- [ ] Unsupported currency blocks auto-post but keeps the invoice approved and exportable.
- [ ] A Xero sandbox proof is recorded before this ticket is accepted.

### 27. QuickBooks Online vertical slice

**What it delivers:** The existing QuickBooks integration is reused safely, with correct currency and audited duplicate protection, and an approved invoice becomes one correct bill in a QuickBooks sandbox.

**Blocked by:** 2, 19, 20, 23, 25.

- [ ] Existing OAuth, realm storage, client, sync classes, and provider adapter are reused, not rebuilt.
- [ ] The connected company name is visible.
- [ ] Supplier and COA imports work; PO sync coverage is verified or explicitly marked unavailable.
- [ ] The hardcoded USD default is removed; the document currency is passed.
- [ ] Duplicate protection follows the common `erp_sync_key` plus pre-flight lookup contract.
- [ ] A timeout reconciles to the existing bill; ambiguity stops without a second POST.
- [ ] Failure stays visible and retryable.
- [ ] A QuickBooks sandbox proof is recorded before this ticket is accepted.

### 28. Sage connection, business selection, and reference-data reads

**What it delivers:** An administrator connects a Sage business, selects it explicitly, and InvoiAI reads only the agreed Sage AP resource areas needed before any write.

**Blocked by:** 1, 2, 19, 20, 24.

- [ ] The verified Sage authorization flow, regional endpoints, scopes, and business-selection mechanism from the ticket 1 ADR are used on **Sage Accounting API 3.1**. No endpoint or header is inferred.
- [ ] The connection screen names the supported Sage Accounting product/edition and never presents a quotes-and-invoicing-only edition as AP-compatible.
- [ ] The callback does not auto-select; the administrator chooses exactly one business returned by **User Accounts**, and its external ID, name, and region are stored.
- [ ] **Contacts** are used for supplier matching only; unnecessary personal and bank details are not imported.
- [ ] **Chart of Accounts** imports active postable accounts idempotently.
- [ ] **Status Codes & Types** are read and reflected in local sync state; no custom status or type is written.
- [ ] **Currencies** are read and reported as supported, rate-required, or unsupported for GBP, USD, and NGN; no conversion is performed.
- [ ] **Taxes** are read and mapped only; no determination, calculation, or filing.
- [ ] Relevant **Settings** are read only as needed; unrelated configuration is not stored.
- [ ] Attachments are not implemented in this slice.
- [ ] A Sage trial-business proof for connection, business selection, and every read above is recorded before acceptance. Sage has no development sandbox.

### 29. Sage Purchase Transactions write-back and boundary enforcement

**What it delivers:** An approved invoice becomes one correct purchase transaction in the selected Sage business, with retry, duplicate protection, and a proven boundary that excludes every unapproved Sage resource.

**Blocked by:** 2, 25, 28.

- [ ] An approved invoice creates one purchase transaction with the original supplier, reference, dates, currency, lines, account references, and existing tax references.
- [ ] The provider status/type is read back and reconciles supplier, reference, amount, currency, date, and line count before the bill is marked synced.
- [ ] Relevant credit notes are created/updated only if ticket 1 verified the capability; otherwise they stay local and are labelled.
- [ ] A rate-required currency needs a human-confirmed rate before retry; an unsupported currency sets `blocked_currency` and keeps the invoice approved and exportable.
- [ ] A timeout reconciles to the existing transaction; a retry cannot create a duplicate; multiple or mismatched matches stop with an ambiguity error.
- [ ] 401/403 prompts reconnect, 429 backs off, 4xx stops with a safe field-level reason, and 5xx retries.
- [ ] The adapter calls no excluded Sage resource, and the negative contract test fails the build if it does.
- [ ] A Sage trial-business proof for one write on API 3.1, timeout reconciliation, duplicate prevention, currency decisions, and excluded resources is recorded before acceptance.

### 30. Cross-provider duplicate, retry, and currency verification

**What it delivers:** The same invoice scenario is proven against Xero, QuickBooks Online, and Sage, and the team has one evidence matrix showing where each provider posts, requires a rate, or blocks a currency.

**Blocked by:** 26, 27, 29.

- [ ] The provider contract suite passes for all three adapters.
- [ ] Each provider creates zero duplicate bills across timeout, retry, reconnect, and concurrent-worker scenarios.
- [ ] Each provider's organization/business header and idempotency behavior are evidenced.
- [ ] GBP, USD, and NGN results are recorded per provider as posted, rate-required, or blocked.
- [ ] Unsupported-currency and rate-required paths keep the invoice approved and exportable.
- [ ] Sage proves its negative boundary: no Banking, Payments & Receipts, bank-account, journal/ledger, Sales, Opening Balances, Products & Services, or Reporting calls.
- [ ] Failure states for 401/403, 429, 4xx, 5xx, and timeout are visible and recoverable in the UI.
- [ ] The evidence matrix distinguishes Xero/QuickBooks sandbox evidence from Sage trial-business evidence on API 3.1 and is attached to the release record.

---

## Payment, dashboard, and launch

### 31. Payment instruction CSV/PDF export and customer-reported status

**What it delivers:** An authorized user can export approved invoices for payment, then record a manual payment status that is always labelled customer-reported.

**Blocked by:** 23.

- [ ] Approved invoices become available for CSV and PDF export.
- [ ] CSV uses fixed decimal formatting, RFC 4180 quoting, and formula-injection protection.
- [ ] PDF or print-optimized output shows the same fields, totals, and a “customer-reported, not bank-verified” label.
- [ ] Exports are organization- and role-scoped and contain no bank credentials.
- [ ] Users can record paid, partially paid, failed, returned, or unknown with date, amount, reference, and note.
- [ ] Status history is append-only, idempotent, and audited.
- [ ] Approved, exported, and customer-reported-paid states are visibly separate.
- [ ] Export works when accounting sync is missing, failed, or blocked by currency.
- [ ] No supplier payment is initiated, executed, or settled.

### 32. AP dashboard, search, quota behavior, billing surface, and cleanup

**What it delivers:** A user lands on an operational AP queue with one clear next action, can search and filter reliably, sees trial/allowance/seat state without it crowding the queue, and never sees personal-finance or free-tier surfaces in the business workspace.

**Blocked by:** 18, 23, 31.

- [ ] The dashboard shows counts and one prioritized next action: Review invoice, Resolve exception, Approve bill, Sync to accounting, Review currency, Export payment instructions, or Report payment.
- [ ] Search and filters cover number, supplier, amount, currency, date, status, and assignee, with URL-persisted state and server pagination.
- [ ] Empty, loading, and error states explain the next step.
- [ ] The manual no-connection state is visible and usable.
- [ ] Quota warns at 80% and 100%; at the limit only new AI/OCR extraction pauses, while manual work, approvals, sync, export, and existing records continue.
- [ ] The dashboard and settings link to the billing surface for trial, invoice allowance, and seats, without duplicating billing controls.
- [ ] The invoice allowance and seat count are shown as separate meters; neither is implied by the other.
- [ ] Personal finance is removed from navigation and redirected; its APIs are not exposed in the business workspace.
- [ ] The vendor portal and bank-change collection are disabled but the code remains gated.
- [ ] The Free plan card and Free price ID are removed; a trial state replaces them.
- [ ] The integrations page shows all three providers, organization/business selection, status, capabilities, edition limits, currency limits, and the Sage verification state.

### 33. Launch hardening and pilot readiness

**What it delivers:** The complete AP MVP passes its acceptance gates in staging with real provider test invoices (Xero/QuickBooks sandbox and a Sage trial business), and the team has the runbooks and pilot onboarding needed to start.

**Blocked by:** 5, 6, 30, 31, 32.

- [ ] Every acceptance criterion in section 7 of the spec is green in staging.
- [ ] Cross-tenant, RLS, decimal, duplicate-bill, webhook-replay, migration, and backup-restore tests pass in CI.
- [ ] Each provider has recorded evidence for organization selection, imports, approved write, timeout reconciliation, and duplicate prevention: Xero and QuickBooks from their sandboxes, Sage from a trial business account on API 3.1.
- [ ] The manual AP path is demonstrated end to end with no accounting connection, including an NGN invoice.
- [ ] Signup completes with email OTP only; optional mobile/SMS does not gate any supported country.
- [ ] Pricing, trial, seat, and allowance acceptance checks pass with approved values; no permanent free plan is present.
- [ ] Public pricing and the authenticated billing surface show the correct GBP/USD values and no invented price.
- [ ] Design and accessibility checks pass for keyboard, screen reader, reduced motion, mobile, and high-contrast AP work screens.
- [ ] Supplier payment execution and bank connectivity remain disabled.
- [ ] Operator runbooks cover stuck workers, provider outages, webhook replay, restore, customer-data deletion, and secret rotation.
- [ ] Pilot onboarding is ready for 3–5 firms with a measured baseline and willingness-to-pay method.
- [ ] The release record states which provider capabilities are verified and which are narrowed or unavailable.

---

## Open items that still gate publication

1. The Sage capability ADR and **Sage trial-business evidence on API 3.1** (ticket 1) do not exist yet, including whether “Sage Accounting Start (Quotes & Invoicing Only)” supports supplier purchase transactions. Sage has no development sandbox.
2. Xero and QuickBooks sandbox proofs have not been run.
3. The manual no-connection path has not been verified end to end.
4. Final GBP/USD prices, monthly invoice allowances, additional-seat rate, and proration need product-owner approval before ticket 12 is implemented with real values. The Solo/Duo/Team seat structure is approved.
5. The approved trial terms are 14 days, 25 processed invoices, no card at signup, and read-only plus export at the end; they no longer gate publication.
6. The optional SMS OTP decision needs provider cost/coverage/friction evidence and product-owner approval. Email OTP alone is sufficient and must remain available in Nigeria.
7. The remaining product-owner decisions in section 9 of the spec still need sign-off; the signup field classification and frontend direction are recorded in the roadmap and spec.
8. The product owner has not approved the 33-ticket split, including the new team/seat, pricing/billing, design, and public-pricing tickets and the separation of Sage reads (28) from Sage write-back (29).
9. No tracker or `ready-for-agent` label has been configured, so this proposal must not be published as issues yet.

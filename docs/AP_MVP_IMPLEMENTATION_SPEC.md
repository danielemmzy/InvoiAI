# InvoiAI AP MVP — Implementation Specification

> **Status:** Reconciled review draft — **Sage AP scope and product direction settled; approved seat/trial structure recorded; final prices, provider verification, and product-owner approval still open**.
> **Date:** 2026-11-08 (supersedes the 2026-11-07 revision)
> **Source of truth:** `docs/PRODUCTION_ROADMAP.md`, including the 2026-11-07 Sage AP scope amendment and the 2026-11-08 signup, team-pricing, and frontend-direction amendment. Where this spec and the roadmap disagree, the roadmap wins.
> **Audience:** Product owner, implementation agent, reviewer.
> **Code changes:** none. This revision reconciles Sage to the agreed AP resource areas, adds the pricing/seat/trial contract, replaces the single long signup with account registration plus resumable business onboarding, and records the frontend design direction. It does not set final prices or trial terms.

## 0. Status, ticket gate, and what is stable

The product owner has confirmed that **Xero, QuickBooks Online, and Sage Accounting are all required MVP accounting integrations**. UK and US remain the primary markets; Nigerian customers must not be blocked from the manual AP workflow.

Sage AP is limited to these **API resource areas**: User Accounts, Contacts, Chart of Accounts, Purchase Transactions, Status Codes & Types, Currencies, Taxes, and relevant Settings. Attachments are optional and are not in the first Sage slice. Those names describe resource areas, not confirmed OAuth permission scopes.

The spec is reconciled to that scope and is ready to drive the ticket breakdown in `docs/AP_MVP_TICKET_PROPOSAL.md`. It is not yet ready to claim provider support or launch because:

1. The exact Sage product/edition/version, regional availability, authorization flow, endpoints, and resource capabilities have not been verified in official documentation and a Sage trial business account on API 3.1 (Sage has no development sandbox).
2. Xero and QuickBooks Online **write-back, currency, duplicate, and retry behavior** has not been verified end to end in their sandboxes, and Sage behavior has not been verified in a trial business account.
3. The **manual AP path** exists in pieces but has not been verified end to end with no accounting connection.
4. The remaining product decisions in section 9 still need product-owner sign-off.

Tickets may be created and reviewed once the product owner approves the breakdown, and non-provider work may start for tickets whose own gates are closed. Sage connector implementation cannot start until the capability verification in 5.5 is recorded, and no provider slice is accepted without its recorded evidence: Xero/QuickBooks sandbox or a Sage trial business account. Sage is not deferred, optional, or awaiting a product-family decision.

### 0.1 Ticket gate

Each gate below blocks the work it names, not the whole plan. The ticket breakdown may be approved and tickets created while gates are open, as long as implementation starts only for tickets whose own gate is closed or explicitly accepted by the product owner. The Sage capability gate blocks Sage connector work only; it does not block manual AP, auth, intake, approvals, or the Xero/QuickBooks foundation.

| Gate | Evidence required | Owner | Status |
|---|---|---|---|
| Sage AP resource scope agreed | Product-owner decision recorded: resource areas, explicit exclusions, optional Attachments | Product owner | **Closed 2026-11-07** |
| Seat structure and trial approved | Product-owner decision recorded: Solo 1 / Duo 2 / Team 5 active seats, additional paid seats, unique-member counting, separate invoice allowance, 14-day trial, 25 processed invoices, no card at signup, read-only plus export at trial end | Product owner | **Closed 2026-11-08** |
| Final plan amounts approved | Product-owner decision recorded: GBP/USD prices, invoice allowances, additional-seat rate, and proration; checkout stays gated until then | Product owner | Open |
| Signup and onboarding shape approved | Product-owner decision recorded: registration fields, verification sequence, resumable onboarding steps, required versus deferred fields, and referral-code omission | Product owner | **Closed 2026-11-08** |
| SMS OTP decision | Provider evaluation recorded: cost per message, country coverage (especially Nigeria), delivery latency, and signup friction versus email OTP; optional recovery/second factor or not adopted. Email OTP remains sufficient either way | Product owner + engineering | Open for optional SMS only |
| Sage product and capability verified | Official documentation plus a **Sage trial business account** (Sage has no development sandbox): **Sage Accounting API 3.1**, product/edition/version (including whether “Sage Accounting Start (Quotes & Invoicing Only)” supports supplier purchase transactions), regional availability, authorization, User Accounts business selection, Contacts, Chart of Accounts, Purchase Transactions (invoices and relevant credit notes), Status Codes & Types, Currencies, Taxes, Settings, and whether Attachments are supported; recorded as a short ADR | Engineering | Open |
| Sage connector feasibility confirmed | Sage trial business account, business selection, purchase-transaction fields, credit-note behavior, currency decisions, rate limits, and no dependency on excluded Sage resources | Engineering | Open |
| Xero write-back verified | Sandbox proof: select tenant, import contacts/accounts/POs, create one `ACCPAY`, reconcile a timeout, retry a `5xx` | Engineering | Open |
| QuickBooks write-back audited | Confirm existing `create_bill`/`update_bill` behavior, duplicate protection, and remove the hardcoded USD default | Engineering | Open |
| Provider currency behavior verified | GBP, USD, and NGN capability tests per provider: posted, rate-required, or blocked | Engineering | Open |
| Manual AP without a connection verified | Upload, review, approve, export, and status tracking work with zero integrations | Engineering | Open |
| Acceptance criteria approved | Product owner signs off on section 7 and the blocking decisions in section 9 | Product owner | Open |

**Commercial gate (does not block AP implementation):** Stripe GBP/USD subscription billing requires account eligibility and legal/tax review. It is tracked separately because AP does not depend on billing. Do not activate paid checkout until it is closed and the owner approves actual GBP/USD prices, invoice allowances, additional-seat rates, and proration. The approved seat structure and trial defaults do not block manual AP, signup, or onboarding.

**Live-launch gate (does not block sandbox development):** accepting live customer data and charging for the service requires the legal, privacy, security, contract, tax, and provider-production items listed in section 9.2. Do not collapse these into an engineering ticket or treat the absence of payment execution as removing them.

### 0.2 Stable decisions versus provisional decisions

**Stable (do not re-litigate without a new product-owner amendment):**

- UK and US are the primary markets.
- Xero, QuickBooks Online, and Sage Accounting are all required MVP accounting choices. Sage is not optional or deferred.
- Sage AP is limited to User Accounts, Contacts, Chart of Accounts, Purchase Transactions, Status Codes & Types, Currencies, Taxes, and relevant Settings. Attachments are optional.
- Sage Banking, Payments & Receipts, bank-account access, general journal/ledger operations, Sales Transactions, Opening Balances, Products & Services, and Reporting are not in the MVP.
- Sage Intacct, Sage 50/50cloud, Sage 100, and Sage X3 are not MVP targets.
- Nigeria must not be blocked from signup or the core AP workflow by geography, provider choice, or currency.
- Manual AP must work with no accounting connection.
- Invoice amounts and currencies are preserved; no silent conversion.
- Supplier payment execution, bank integrations, automated tax determination/filing, advanced FX, AR, multi-entity, and full procurement remain out of scope.
- Stripe is for InvoiAI subscription billing only.
- Plans bundle a monthly workspace invoice-processing allowance and a number of included user seats. Seat limits and invoice allowances are separate; billing never depends on supplier-payment count.
- The approved starting structure is **Solo** (1 active seat), **Duo** (2), and **Team** (5), with additional paid seats. Final prices, allowances, additional-seat rates, and proration remain unapproved.
- Each unique active workspace member consumes one seat regardless of role; pending invitations, removed members, and disabled members do not.
- There is no permanent free tier. The approved trial is 14 days, up to 25 processed invoices, no card at signup, then read-only plus export if no paid plan is chosen.
- UK plans are priced in GBP and US plans in USD. Nigeria billing and Stripe eligibility are a separate verification item and never block signup or manual AP.
- Signup is a short account-registration step followed by a resumable business-onboarding flow, not one long form.
- Company registration number and tax ID are never required to create an account, start a trial, or use manual AP.
- Country sets currency, date, and number formatting defaults only; it never determines tax treatment, creates a tax obligation, or files anything.
- Email verification is the primary path; mobile/SMS is optional and must not block signup. Referral-code collection is omitted unless an existing launch purpose is confirmed.
- The supported Sage Accounting product/edition is shown during connection setup, and a quotes-and-invoicing-only edition is not presented as AP-compatible unless verified.
- Reuse the existing FastAPI/Postgres-Supabase/Redis/worker/Next.js architecture; the existing UI stack is Next.js, Tailwind, Radix, Lucide, React Query, React Hook Form, and Zod.

**Provisional (must be resolved before the affected work is accepted):**

- The exact Sage Accounting product/edition/version on API 3.1, regional availability, authorization flow, endpoints, and response shapes.
- Whether “Sage Accounting Start (Quotes & Invoicing Only)” supports supplier purchase transactions and can be offered as AP-compatible.
- Which Sage resource areas are actually available and writable for the authorized app, including credit notes and optional Attachments.
- Which currencies each provider can post, and under what account configuration.
- Whether the existing QuickBooks duplicate protection is sufficient.
- The exact Xero write-back fields and reconciliation query.
- Final GBP/USD prices, invoice allowances, additional-seat rates, and proration behavior. The Solo/Duo/Team seat structure and 14-day/25-invoice/no-card trial are approved.
- The billing entity and Stripe GBP/USD product configuration.
- Whether optional SMS OTP is adopted, and which provider covers Nigeria. Email OTP alone is approved and sufficient.

### 0.3 Development and provider-test environments versus live launch

These are separate workstreams and must not be reported as one gate.

**Required to build and test against providers:**

- Developer/partner accounts and test apps for Xero and QuickBooks Online sandboxes, plus a Sage developer app and a Sage trial business account (Sage has no development sandbox).
- Redirect URIs, test businesses/companies, resource permissions, regional endpoints, and test data.
- A staging database and CI environment that reproduce the production migration chain.
- Test credentials for Google OAuth, transactional email, and Stripe test mode where the relevant feature is being built.
- Recorded evidence for each provider slice: Xero and QuickBooks sandbox evidence, and Sage trial-business evidence using API 3.1.

**Required before accepting live customer data or charging for the service:**

- A decided contracting entity and customer terms.
- Privacy notice, data-processing agreements, subprocessor list, international-transfer safeguards, retention/deletion policy, and data-subject-request process.
- Security review, incident-response ownership, breach-notification process, and appropriate insurance.
- Production app approval and terms for each accounting provider.
- Stripe live-account eligibility, settlement, tax, and GBP/USD product configuration.
- Market-specific tax and billing review for the UK and US, and Nigeria-specific validation before any localization claim.
- Confirmed hosting region and any required data-protection assessment.

Do not block sandbox development on business-formation questions unless a provider's own access rules require the entity to exist first.

---

## 1. Product direction

| Decision | MVP contract |
|---|---|
| Primary markets | UK and US small and medium-sized professional-services firms, consultancies, agencies, and finance teams. |
| Secondary / supported | Nigeria and other countries may sign up and use the manual AP workflow. Do not block them by IP, country, currency, or provider choice. |
| Accounting providers | Xero, QuickBooks Online, and Sage Accounting are required MVP choices. At most one active accounting connection per workspace at launch. |
| Sage AP scope | User Accounts (business selection), Contacts (supplier matching), Chart of Accounts, Purchase Transactions (approved supplier invoices and relevant credit notes), Status Codes & Types, Currencies, Taxes (read/map only), and relevant Settings. Attachments are optional and not in the first slice. |
| Sage exclusions | No Sage Banking, Payments & Receipts, bank-account access, general journal/ledger operations, Sales Transactions, Opening Balances, Products & Services, or Reporting. Do not call excluded resources even when the API exposes them. |
| Sage verification | The names above are resource areas, not confirmed OAuth scopes. The exact product/edition/version, region, authorization, endpoints, and capabilities must be verified in official documentation and a **Sage trial business account on API 3.1** before implementation. Sage Business Cloud Accounting API has no development sandbox; do not require or claim one. |
| Manual AP | Upload, email intake, extraction, review, matching, coding, approval, payment-instruction export, and customer-reported status work without any accounting connection. |
| Workspace currency | UK defaults to GBP; US defaults to USD; Nigeria may default to NGN; other countries select an ISO currency. The user may change the workspace currency during onboarding. |
| Invoice currency | Always preserve the invoice's original amount and ISO currency, including NGN. |
| Provider currency limits | If a provider cannot post the invoice currency, explain why, keep the invoice approved in InvoiAI, and keep manual payment-instruction export available. Do not silently convert. |
| Subscription billing | Stripe subscription billing only. Price UK plans in GBP and US plans in USD only after account eligibility and tax/legal review. Supplier payment execution is unrelated and remains out of scope. |
| Plan structure | **Approved starting structure:** **Solo** (1 active seat), **Duo** (2), **Team** (5), each with a monthly invoice allowance; additional seats are a paid per-seat add-on. Each unique active member counts once regardless of roles. Final prices, allowances, additional-seat rates, and proration remain unapproved. |
| Trial | **Approved trial:** 14 days, up to 25 processed invoices, no card at signup, then read-only plus export if no paid plan is chosen. Distinct from a permanent free plan; no permanent free tier. |
| Signup | Short account registration (first name, surname, business email, password or Google; optional mobile) followed by a resumable business-onboarding flow. No company registration number, tax ID, or card required to create an account or start a trial. |
| Verification | Email OTP/verification is primary. SMS OTP is evaluated as an optional recovery or second factor, not a mandatory parallel step. Nigeria must complete signup and manual AP when SMS is unavailable. |
| Country behavior | Country sets currency, date, and number formatting defaults only. The user may override currency. Country never determines tax treatment or files tax. |
| Frontend direction | UI/UX Pro Max for the authenticated product; Scroll Craft for the public landing/pricing journey only. Restrained glass and a few dimensional moments, kept off dense tables, forms, review, and approval screens. |
| Launch boundary | No supplier payment execution, no bank connection, no automated tax determination/filing, no e-invoicing, no AR, no multi-entity consolidation, no advanced FX. |

---

## 2. Problem statement

UK and US small and medium-sized professional-services firms already use Xero, QuickBooks Online, or Sage, but their supplier-invoice process is split across inboxes, spreadsheets, shared drives, and ad-hoc approvals. The work is slow, the audit trail is weak, and the same invoice can be paid twice or posted to the accounting system incorrectly.

The current InvoiAI codebase has a broad but uneven AP foundation:

- Authentication is email/password with link-based verification; signup collects no name or mobile; there is no `/onboarding` route, and workspace creation at `/workspace` only partly captures the business profile.
- The billing catalog is USD-only, still includes a permanent Free tier, sends Stripe checkout with quantity 1, has no trial, and enforces no seat limit even though `seat_limit_for` exists.
- The invite UI exposes owner/admin/manager/member instead of the three AP roles, and no surface shows included, used, or pending seats.
- QuickBooks has OAuth, sync classes, a `QuickBooksAccountingProvider`, and an approved-bill path, but the bill payload defaults currency to USD and duplicate protection has not been audited.
- Xero has OAuth and inbound sync, but the callback auto-selects the first tenant, the client is GET-only, and there is no Xero accounting-provider adapter, chart-of-accounts import, or approved-bill write-back.
- Sage exists only as an `IntegrationProvider` enum value. There is no Sage OAuth client, sync, or provider adapter. The AP resource scope is agreed, but the exact Sage product/version, regional endpoints, authorization, and field contracts still need verification.
- Chart-of-accounts sync is hardcoded to QuickBooks.
- The integrations screen is QuickBooks-centric and the tax-mapping editor only knows QuickBooks and Xero.
- Matching, coding, approval, payment instructions, and document review exist, but they are not connected into one trustworthy end-to-end path.
- A customer with no accounting connection has no clearly designed path through the product.

The customer cannot yet sign up, verify their email, describe their business, upload or forward an invoice, correct extraction, match it to a PO or receipt, approve it with the right authority, create a bill safely in their chosen accounting system, export a payment instruction, and track a customer-reported payment with confidence that no step was skipped or duplicated.

---

## 3. Solution

Deliver one complete AP workflow for UK and US customers who use Xero, QuickBooks Online, Sage, or no accounting system:

**sign up → verify email → onboard workspace, team, and plan → upload or forward invoice → extract and validate → review duplicates/anomalies → code supplier and GL → match PO/receipt → approve → create a bill in the selected accounting system when supported → export payment instructions → record customer-reported payment status**

The solution reuses the existing FastAPI monolith, Supabase/Postgres, Redis, worker abstractions, AP domain models, approval engine, document intake, and encrypted token service. It adds only the seams needed to close verified gaps:

- A real identity layer: name, six-digit OTP verification, Google OAuth, administrator TOTP MFA with recovery codes, and backend enforcement of verification and authorization.
- A guided business onboarding flow that creates the first workspace and assigns its creator as owner.
- A single document record and review surface for upload and forwarding-email intake.
- Multi-PO and multi-receipt matching with line-level partial allocation and configurable tolerances.
- A **provider-neutral accounting adapter** implemented by Xero, QuickBooks Online, and Sage Accounting, with organization/business selection, supplier/COA/PO import where supported, approved-bill write-back, idempotency, retries, visible failures, and duplicate protection. The Sage adapter is limited to the agreed AP resource areas.
- An explicit **manual AP path** that never requires an accounting connection.
- A payment handoff that exports CSV/PDF and records customer-reported status without executing payments.
- Frontend flows, loading/empty/error states, and cache rules that make the workflow usable rather than merely available as API endpoints.

AI extracts, checks, and suggests. People code, approve, and decide. InvoiAI never moves money in this MVP.

---

## 4. User stories

### Authentication and account security

1. As a new business user, I want to register with my first name, surname, business email, and password, so that my account is identifiable without completing a long form.
2. As a new user, I want to sign up with Google, so that I do not have to create and remember another password.
3. As a new user, I want to add my mobile number with a country code when it suits me, so that I can receive recovery or notification messages without blocking registration.
4. As a user who signed up with a password, I want to receive a six-digit email code, so that I can prove I own the business email address.
5. As a user entering an OTP, I want the six digits to fill and advance automatically, so that verification is quick and not error-prone.
6. As a user entering an OTP, I want to paste a code, so that I can use a code copied from my email.
7. As a user, I want to see how long the code remains valid, so that I know whether to resend it.
8. As a user, I want to resend the code after a short cooldown, so that I am not blocked by a lost email.
9. As a user, I want to see how many attempts remain, so that I understand when the code will be locked.
10. As a user with an expired or locked code, I want a clear recovery path, so that I can verify my email without contacting support.
11. As a user in a country where SMS delivery is unreliable, I want email verification to be sufficient, so that I can still complete signup and manual AP.
12. As a user, I want SMS as an optional recovery or second factor where available, so that I am not forced to use it but can strengthen access if I choose.
13. As a user, I want to log in with my email and password, so that I can return to my workspace.
14. As a returning user, I want a saved session that refreshes safely, so that I am not logged out during normal work.
15. As a user, I want to log out, so that my session cannot be reused on a shared device.
16. As a user who forgot my password, I want to request a reset without revealing whether an email exists, so that my account is not enumerable.
17. As a user resetting my password, I want a secure, expiring reset flow, so that my account cannot be taken over through an old link.
18. As an owner or administrator, I want TOTP MFA with recovery codes, so that a stolen password alone cannot reach organization settings or financial actions.
19. As an administrator, I want MFA to be separate from email verification, so that verifying an email address does not weaken account security.
20. As an administrator, I want a step-up MFA challenge before sensitive actions, so that role changes, accounting reconnects, and exports are protected.
21. As an administrator, I want to regenerate or use recovery codes, so that I can recover access if I lose my authenticator.
22. As an unverified user, I want to be sent back to verification, so that I cannot accidentally use protected business features.
23. As a security reviewer, I want every protected API route to reject unverified users and non-members, so that frontend route filters are not the only control.
24. As a user, I want clear rate-limit and invalid-credential messages, so that I know what to do next without exposing account details.
25. As a user, I want my session revoked after logout, password change, or membership removal, so that old access cannot continue.
26. As an owner, I want the last-owner rule enforced, so that a workspace cannot be left without an administrator.
27. As a user, I want Google accounts linked only when the provider email is verified, so that someone cannot merge into my account with an unverified address.
28. As a user, I want authentication events recorded, so that suspicious access can be reviewed.

### Business onboarding and workspace

1. As a newly verified user, I want a short, resumable onboarding wizard, so that I can set up my business without a long form and without losing progress.
2. As a user, I want to enter my business/workspace name, so that my workspace is recognizable to my team.
3. As a user, I want to choose my business country, so that the workspace defaults to the right currency and format.
4. As a UK user, I want the workspace to default to GBP, so that invoices and approval limits use my operating currency.
5. As a US user, I want the workspace to default to USD, so that invoices and approval limits use my operating currency.
6. As a Nigerian user, I want to sign up and use the AP workflow without being blocked by my country, currency, or unavailable SMS, so that I can evaluate the product.
7. As a user outside the UK/US, I want to choose my workspace currency from the supported ISO list, so that the workspace reflects my business.
8. As a user, I want to override the country-derived default currency, so that the workspace matches how the business actually operates.
9. As a user, I want to select my business type or registration status, including “not yet registered,” so that I am not forced to invent a company number.
10. As a user, I want to select my industry, so that coding suggestions and terminology fit my business.
11. As a user, I want to select my team-size band, so that the product can recommend the right seat plan.
12. As a user, I want to select my approximate monthly supplier-invoice volume, so that the invoice allowance recommendation is appropriate.
13. As a user, I want to select my accounting software from Xero, QuickBooks Online, Sage Accounting, none, or not sure, so that InvoiAI can guide me without forcing a connection.
14. As a user who does not use accounting software, I want to continue with manual AP, so that I am not blocked from the product.
15. As a user, I want to be told which Sage Accounting product/edition is supported, so that I do not connect a quotes-and-invoicing-only edition that cannot handle supplier bills.
16. As a user, I want to skip optional onboarding questions, so that I can start processing invoices quickly.
17. As a user, I want to edit onboarding answers later in settings, so that the workspace stays accurate as the business changes.
18. As a user, I want onboarding to resume if I leave midway, so that I do not lose entered information.
19. As a user, I want to be asked for a company registration number or tax ID only when a specific billing or accounting step needs it, so that signup and trial stay frictionless.
20. As a workspace creator, I want to become owner/admin automatically, so that I can invite my team and configure the workspace.
21. As a workspace creator, I want to invite a reviewer or approver during onboarding, so that approval is ready before the first invoice arrives.
22. As a workspace creator, I want to see how an invitation affects my seat count, so that I understand the next charge before sending it.
23. As a workspace creator, I want a workspace switcher, so that I can move between workspaces without confusing context.
24. As a workspace member, I want to belong to more than one workspace, so that I can work with more than one business.
25. As an owner, I want to invite colleagues and assign Workspace Admin, Invoice Reviewer, or Approver roles, so that reviewers and approvers can do their jobs.
26. As a member, I want navigation and actions filtered by my role, so that I do not see controls I cannot use.
27. As an owner, I want to remove a member and revoke their access immediately, so that departing staff cannot read financial records and their seat is released.
28. As a reviewer, I want to see the active workspace name everywhere, so that I never approve the wrong company's invoice.
29. As a user switching workspace, I want cached business data cleared, so that one company's records never appear under another company's name.
30. As a user logging out, I want all cached business data cleared, so that the next person on the device sees nothing.
31. As a user, I want onboarding to explain why each question is asked, so that I can decide whether to answer it.
32. As a user, I want accessible forms with labelled fields and readable errors, so that I can complete onboarding with a keyboard or screen reader.

### Pricing, seats, and trial

1. As an owner, I want plans defined by a monthly invoice allowance plus included seats, so that I can match the plan to how my team actually works.
2. As a one-person business, I want a single-seat plan, so that I do not pay for unused seats.
3. As an owner who reviews with one other person, I want a two-seat plan, so that a reviewer or approver can work without an add-on.
4. As a small finance team, I want a plan with several included seats, so that the whole team can work in one workspace.
5. As an owner, I want to buy additional seats at a clear per-seat rate when I outgrow the included seats, so that I am not forced to jump tiers.
6. As an owner, I want to see included seats, used seats, pending invitations, and the next charge in one place, so that I can predict cost.
7. As an owner, I want a member with several roles to count as one seat, so that permissions do not inflate my bill.
8. As an owner, I want pending invitations and removed members not to count as seats, so that I am charged for active people only.
9. As an owner, I want a warning before I hit the seat limit, so that I can decide whether to add seats or remove access.
10. As an owner, I want the invoice-processing allowance and the seat count shown separately, so that I understand which limit I am approaching.
11. As an owner, I want approval, export, and supplier-payment-instruction activity to never consume the invoice allowance, so that billing reflects invoices processed, not payments.
12. As a new customer, I want a time-limited trial with a visible end date and invoice cap, so that I know what is included and what happens next.
13. As a trial user, I want to use the product without entering a card, so that I can evaluate it before committing.
14. As a trial user, I want to choose a plan before the trial ends, so that my records and workflow continue.
15. As a trial user whose trial ended without a plan, I want read-only access plus export, so that I can still retrieve my data and decide.
16. As a UK customer, I want to see plan prices in GBP, so that I know what I will be charged.
17. As a US customer, I want to see plan prices in USD, so that I know what I will be charged.
18. As an owner, I want to see my current plan, renewal date, invoices, and payment method, so that I can manage billing without contacting support.

### Upload and email intake

1. As an AP clerk, I want to upload a PDF or image invoice, so that it enters the review workflow.
2. As an AP clerk, I want to drag and drop multiple invoices, so that I can process a batch.
3. As an AP clerk, I want the upload to reject unsupported or oversized files with a clear reason, so that I can fix the file.
4. As an AP clerk, I want to see upload progress and per-file outcomes, so that I know which files succeeded.
5. As an AP clerk, I want an organization-specific forwarding address, so that suppliers can keep emailing invoices to a familiar address.
6. As an AP clerk, I want emailed attachments to become the same kind of document as an upload, so that there is one queue and one review surface.
7. As an AP clerk, I want duplicate emails and attachments to be ignored idempotently, so that a retried provider webhook does not create two documents.
8. As a security reviewer, I want SPF, DKIM, and DMARC failures quarantined, so that spoofed invoices are not silently accepted.
9. As a security reviewer, I want attachments scanned before processing, so that malware does not reach OCR or storage previews.
10. As a security reviewer, I want email and upload rate limits, so that an attacker cannot exhaust processing capacity.
11. As an AP clerk, I want cross-channel duplicate detection, so that an invoice emailed and uploaded twice is flagged once.
12. As an AP clerk, I want a clear processing timeline, so that I know whether a document is queued, reading, extracting, or failed.
13. As an AP clerk, I want a retry action for failed processing, so that a transient OCR failure does not require re-upload.
14. As an AP clerk, I want the original file preserved, so that I can compare it with extracted values.
15. As an AP clerk, I want a visible quota warning before the processing limit, so that I am not surprised when AI extraction pauses.
16. As a workspace owner, I want manual work, approvals, accounting sync, and exports to continue at the quota limit, so that my business is not locked out.

### Extraction, validation, duplicates, and anomalies

1. As a reviewer, I want header fields extracted with confidence, so that I know which values to check.
2. As a reviewer, I want line items extracted with quantities, unit prices, tax, and totals, so that I can match and code at line level.
3. As a reviewer, I want the source document beside the extracted values, so that I can verify evidence without switching screens.
4. As a reviewer, I want arithmetic validation of subtotal, tax, and total, so that incorrect invoices are caught before approval.
5. As a reviewer, I want date and currency validation, so that impossible dates and unsupported currencies are flagged.
6. As a reviewer, I want duplicate candidates explained, so that I can decide whether to keep or reject the invoice.
7. As a reviewer, I want suspected duplicates never silently deleted, so that a legitimate repeat invoice is not lost.
8. As a reviewer, I want an unknown supplier flagged, so that I can create or link the supplier before coding.
9. As a reviewer, I want anomalies grouped in one queue with severity, so that I can prioritize the riskiest invoices.
10. As a reviewer, I want to correct a field and see who changed what, so that the audit trail is trustworthy.
11. As a reviewer, I want the raw extraction preserved after correction, so that I can compare what the model read with what was approved.
12. As a reviewer, I want totals recalculated with decimal precision, so that rounding does not create approval or payment errors.
13. As an approver, I want unclear or mismatched invoices blocked from approval, so that I do not approve something unresolved.
14. As a compliance reviewer, I want AI output treated as a suggestion, so that a confident model cannot approve or post anything.

### Vendors, chart of accounts, POs, receipts, and matching

1. As an AP clerk, I want suppliers imported from my connected accounting system, so that I do not re-enter vendors I already maintain.
2. As an AP clerk, I want to create a supplier manually, so that I can process an invoice when no accounting system is connected.
3. As an AP clerk, I want to link an extracted supplier to an existing vendor, so that bills and coding use the correct master record.
4. As an AP clerk, I want the chart of accounts synchronized from my connected provider, so that GL coding uses real account codes.
5. As an AP clerk, I want to seed starter accounts when no provider is connected, so that I can still code invoices manually.
6. As an AP clerk, I want to see when the chart of accounts was last synchronized, so that I know coding is based on current data.
7. As an AP clerk, I want purchase orders imported from my connected provider when it supports them, so that matching uses the accounting system's source of truth.
8. As an AP clerk, I want to create or import a basic PO when my provider does not support POs or is not connected, so that I can still match.
9. As an AP clerk, I want to know when my connected provider has no purchase-order API, so that I am not promised a sync that cannot happen.
10. As an AP clerk, I want to record a goods receipt manually, so that three-way matching works even though accounting systems generally have no receipt object.
11. As an AP clerk, I want to import goods receipts by CSV, so that a large delivery can be recorded quickly.
12. As an AP clerk, I want partial receipts to accumulate against a PO line, so that multiple deliveries can be matched over time.
13. As an AP clerk, I want an invoice to reference zero, one, or many POs, so that consolidated supplier invoices can be matched correctly.
14. As an AP clerk, I want an invoice line allocated across PO lines and receipts, so that partial invoices and partial deliveries are represented accurately.
15. As an AP clerk, I want configurable price, quantity, and tax tolerances, so that trivial rounding does not create busywork.
16. As an approver, I want an out-of-tolerance invoice routed to exceptions, so that a mismatch cannot be approved by default.
17. As an approver, I want to waive a mismatch only with a written reason, so that exceptions are deliberate and auditable.
18. As a reviewer, I want a successful match never to auto-approve, so that human control is preserved.
19. As a reviewer, I want a PO change after allocation to flag the match for review, so that the allocation is not silently rewritten.
20. As a reviewer, I want allocated receipts to be voidable only with a reason, so that confirmed evidence is not erased casually.
21. As an AP clerk, I want rule-based GL coding from vendor and description patterns, so that recurring invoices are coded consistently.
22. As an AP clerk, I want AI-suggested coding with an explanation, so that I can accept or correct it.
23. As a reviewer, I want to approve line-level coding before bill creation, so that no line posts to an unapproved account.
24. As a reviewer, I want a line without a valid account blocked, so that incomplete coding cannot reach the accounting system.
25. As a finance manager, I want coding rules and tolerances configurable by administrators, so that policy lives in the product rather than in code.

### Approval

1. As an approver, I want a queue of invoices awaiting my decision, so that I know what needs action.
2. As an approver, I want to see the amount, supplier, due date, coding, matching result, and exception history on one screen, so that I can decide without hunting.
3. As an approver, I want to approve, request changes, or reject with a reason, so that the outcome is clear and auditable.
4. As an approver, I want my approval limit enforced in workspace currency, so that I cannot approve above my authority.
5. As a submitter, I want to be blocked from approving my own invoice above the configured self-approval threshold, so that separation of duties is preserved.
6. As an owner or administrator, I want to self-approve below the threshold with an audit event, so that small invoices do not create needless bottlenecks.
7. As a finance manager, I want foreign-currency invoices compared at the invoice-date rate, so that limits are applied consistently.
8. As a finance manager, I want foreign-currency invoices flagged for FX review, so that currency treatment is deliberate.
9. As an approver, I want a change to supplier, invoice number/date, currency, total, tax, line amount, GL coding, or allocation to revoke approval, so that I never approve one thing and post another.
10. As an approver, I want an overdue approval escalated, so that invoices do not stall indefinitely.
11. As an administrator, I want delegations to expire automatically, so that temporary authority does not become permanent.
12. As a reviewer, I want approval history and comments preserved, so that decisions can be reconstructed.
13. As an approver, I want a match or coding exception to block approval unless waived by an authorized person, so that unresolved risk cannot slip through.
14. As a workspace owner, I want only administrators to change limits and delegations, so that authority cannot be self-granted.
15. As an auditor, I want every approval decision to record actor, time, amount, currency, authority, and reason, so that the decision is defensible.

### Accounting connections and bill write-back — all providers

1. As an administrator, I want to see Xero, QuickBooks Online, and Sage as available accounting choices, so that I can connect the system my business actually uses.
2. As an administrator, I want to connect a provider from the integrations page, so that I can enable accounting sync.
3. As an administrator, I want to choose the correct organization or company after authorizing, so that bills do not go to the wrong tenant, realm, or business.
4. As an administrator, I want the app never to auto-select the first authorized organization, so that I cannot post to the wrong company by accident.
5. As an administrator, I want to see the connected organization name and connection status, so that I know which company is linked.
6. As an administrator, I want to see the last successful sync and the last error, so that I can diagnose problems.
7. As an administrator, I want to reconnect or disconnect a provider, so that I can recover from expired credentials or stop syncing.
8. As an administrator, I want to switch organization only after an explicit confirmation and sync check, so that existing bills are not orphaned.
9. As an administrator, I want switching to a different accounting provider to require confirmation and a check for approved-but-unsynced bills, so that one workspace does not post to two ledgers silently.
10. As an AP clerk, I want suppliers and chart of accounts imported from my connected provider, so that coding uses current accounting data.
11. As an AP clerk, I want purchase orders imported when my provider supports them, so that matching uses the provider's source of truth.
12. As an AP clerk, I want a clear explanation when my provider has no purchase-order API, so that I can use manual or CSV POs instead.
13. As an approver, I want an approved invoice to create a bill automatically or on a clear action, so that I do not re-enter it.
14. As a finance manager, I want a bill created only after approval and authorization checks, so that unapproved liabilities cannot be posted.
15. As a finance manager, I want retries to be idempotent, so that a timeout does not create a duplicate bill.
16. As a finance manager, I want a failed sync to stay visible and retryable, so that I can recover without a database patch.
17. As a finance manager, I want the local invoice linked to the provider bill ID, so that later status and reconciliation are unambiguous.
18. As a finance manager, I want the original invoice currency and amount preserved, so that no conversion is hidden.
19. As a finance manager, I want the app to tell me when the provider cannot post my invoice currency, so that I can review it instead of discovering a silent conversion.
20. As a finance manager, I want unsupported-currency invoices to remain approvable and exportable for manual payment, so that an accounting limitation does not block my AP process.
21. As an auditor, I want every sync attempt, provider response ID, error, and retry recorded, so that duplicate protection is provable.
22. As an administrator, I want token failures to prompt reconnect rather than silent failure, so that sync does not stall unnoticed.
23. As a finance manager, I want provider rate limits handled with backoff, so that a busy period does not create a storm of failed jobs.
24. As a user with no accounting connection, I want the manual AP workflow to remain fully available, so that I can use InvoiAI before I connect anything.
25. As an administrator, I want to connect a provider later without losing existing invoices or approvals, so that adoption is gradual.
26. As a finance manager, I want a local void/archive to be clearly distinguished from voiding the provider bill, so that I do not assume the ledger was reversed.

**Sage-specific boundaries**

1. As an administrator, I want InvoiAI to use Sage only for business selection, suppliers, chart of accounts, purchase transactions, status codes, currencies, tax references, and relevant settings, so that banking, payments, sales, and reporting data are untouched.
2. As an administrator, I want to choose the correct Sage business after authorizing, so that purchase invoices do not land in the wrong company.
3. As an AP clerk, I want Sage contacts used only for supplier matching, so that unnecessary personal or bank details are not copied.
4. As a finance manager, I want Sage tax references read and mapped, not determined, so that InvoiAI never makes a tax decision.
5. As a finance manager, I want Sage currencies checked before a write, so that an unsupported currency is explained instead of silently converted.
6. As an auditor, I want confirmation that no excluded Sage resource was called, so that the integration stays within the agreed AP boundary.

### Payment instructions and customer-reported status

1. As an approver, I want approved invoices to become available for payment instruction export, so that my finance team can pay them through the bank.
2. As a finance manager, I want a CSV export with supplier, invoice, amount, currency, due date, and reference, so that I can upload it to my banking process.
3. As a finance manager, I want a printable PDF instruction sheet, so that I can review and authorize payments on paper or in a meeting.
4. As a finance manager, I want exports scoped to the active workspace and permitted role, so that another tenant cannot obtain my payment data.
5. As a finance manager, I want to record that a payment was made, including date, amount, reference, and note, so that the invoice leaves the queue.
6. As a finance manager, I want that status labelled customer-reported, so that nobody mistakes it for bank-verified settlement.
7. As a finance manager, I want payment status history preserved, so that I can correct a mistake without losing the prior report.
8. As a finance manager, I want to see approved, exported, and customer-reported-paid states separately, so that I know what actually happened.
9. As a security reviewer, I want supplier payment execution and bank integrations disabled, so that InvoiAI cannot move money.
10. As a finance manager, I want the export to exclude bank credentials, so that payment data is not used as a credential store.
11. As an operator, I want export and status changes audited, so that a payment dispute can be investigated.

### Search, queues, operations, and accessibility

1. As an AP clerk, I want to search invoices by number, supplier, amount, date, and status, so that I can find a record quickly.
2. As an AP clerk, I want URL-persisted filters, so that I can share a queue view with a colleague.
3. As an AP clerk, I want a prioritized next action on each record, so that I always know what to do.
4. As an AP clerk, I want empty, loading, and error states that explain the next step, so that I am not left with a blank screen.
5. As a user, I want keyboard navigation and visible focus, so that I can work without a mouse.
6. As a user with reduced-motion preference, I want animations minimized, so that the interface remains comfortable.
7. As a mobile user, I want the review and approval screens to remain usable, so that I can approve from a phone.
8. As an owner, I want personal-finance navigation and routes disabled in the business workspace, so that AP data does not mix with personal data.
9. As an owner, I want a support path and audit history, so that problems can be resolved without direct database access.

---

## 5. Implementation decisions

Subsections 5.1–5.5 are the cross-cutting decisions: reuse map, provider capability matrix, currency matrix, workstream matrix, and the Sage AP scope and verification contract. The detailed workstreams that follow them are numbered 1–16 for continuity with the earlier review draft; they sit under this section, not at the document's top level.

### 5.1 Reuse map: what exists, what is missing, and the smallest seam

| Area | Reusable now | Verified gap | Smallest implementation seam |
|---|---|---|---|
| Authentication | Supabase email/password auth, encrypted BFF session cookie, `AuthUser.is_verified`, logout/refresh, password reset routes | No name at signup; link-based verification; no six-digit OTP; no Google identity flow; no MFA factors or recovery codes; verification not enforced on every protected router | Extend `AuthRepository`/`AuthService`, add `VerificationService` and `MfaService`, wrap protected routers with a verified-user dependency, keep the existing BFF cookie |
| Onboarding | Workspace creation, owner membership, organization settings, workspace switcher, `WorkspaceCreate` with country/currency/company size | No industry choice, invoice volume, accounting software, business role, draft/resume state, or onboarding-complete flag; currency defaults are not market-aware | Extend `WorkspaceCreate` and `OrganizationService.create_workspace`; add a thin onboarding router that reuses the same creation method atomically; add a country→currency default map |
| Upload | `DocumentUploadService` with SHA-256 hashing, storage, duplicate exception, document records | Duplicate detection is file-hash first and not yet cross-channel; quarantine/scanning state is incomplete | Extend the existing upload service and duplicate checker; do not create a second intake service |
| Email intake | `EmailIntakeService` with idempotent attachment keys, size/type checks, HMAC-authenticated webhook, per-org address | SPF/DKIM/DMARC result ingestion, quarantine state, malware scanning, and sender reputation are not proven | Extend the existing email service and webhook contract; add auth-result and scan-status fields to the existing event row |
| OCR/extraction | `OCRWorker`, extraction engine, analysis worker, line-item service, verification engine, duplicate checker | Evidence/confidence is not consistently surfaced; line-item completeness and cross-channel dedupe need verification | Keep the existing worker chain; extend analysis output and review payloads rather than adding an extraction service |
| Vendors | Vendor service, vendor sync, external IDs, vendor controls | Imports are provider-specific; no single provider-neutral import command; no manual-only path surfaced | Extend vendor sync with provider dispatch; keep the vendor domain |
| Chart of accounts | COA service, cache, seed, coding rules, GL coding service | `sync_from_quickbooks()` and `/ap/chart-of-accounts/sync` are hardcoded to QuickBooks | Add provider dispatch inside the existing COA service; keep the Redis cache and seed path |
| POs/receipts | PO routes, goods receipt routes, PO/receipt repositories, matching service, tolerances, exception repository | No persisted line-level allocation across multiple POs/receipts; partial accumulation is computed, not allocated; no provider capability flag for PO sync | Add one allocation table and repository method; extend `MatchingService` to read/write it; add `supports_purchase_orders` to the provider contract |
| Approvals | Approval engine, routing engine, authority service, SoD service, limits, delegations, workflow history | Explicit self-approval threshold, FX-at-invoice-date comparison, and critical-field reapproval are incomplete or not enforced end to end | Extend the existing approval engine and bridge; do not add a second workflow system |
| Provider abstraction | `AccountingProvider` ABC, `get_accounting_provider()`, `QuickBooksAccountingProvider` | Factory raises `NotImplementedError` for Xero and has no Sage branch; interface lacks organization listing/selection and currency validation | Extend the ABC and factory; implement Xero and Sage adapters beside QuickBooks |
| QuickBooks Online | OAuth, realm storage, client, `create_bill`/`update_bill`, vendor/COA sync classes, `BillSyncService`, `BillSyncWorker` | `BillSyncService` hardcodes QuickBooks and defaults currency to USD; duplicate protection relies on local `erp_bill_id` and create-vs-update; PO sync coverage must be confirmed | Reuse the existing client and sync classes; remove the USD default; add provider-neutral payload and reconciliation |
| Xero | OAuth, token refresh, tenant header, inbound contacts/bills/POs/payments sync, `XeroWorker` | Callback auto-selects `connections[0]`; client is GET-only; no COA/supplier/PO import command; no accounting-provider adapter | Add `XeroAccountingProvider`; extend the Xero client with POST/PUT and organization listing; add import commands |
| Sage | Only `IntegrationProvider.SAGE` and domain references | No OAuth, client, sync, or provider adapter; exact product/version, regional endpoints, authorization, and resource capabilities unverified | Complete the verification in 5.5; then add a Sage Accounting client/adapter behind the same ABC, limited to the agreed AP resource areas |
| Bill sync | `BillSyncWorker` compare-and-set claim, provider `create_bill`, local verification, error rollback, payment authorization evaluation | Worker is effectively QuickBooks-specific; no generic provider selection; no currency gate; no reconciliation query | Make the worker provider-neutral; add `find_bill`/reconciliation to the ABC; persist provider sync state |
| Payment instructions | Instruction and event tables, state machine, authorization queue, export buttons for a single document | No batch payment CSV/PDF export; no append-only customer-reported status | Add a payment export service and a small status-report table/routes |
| Frontend | Next App Router, React Query, React Hook Form, Zod, Radix, Tailwind, Lucide, AP pages, document review components | Auth pages are email/password and link-verification only; integrations page is QuickBooks-centric; no OTP, Google, MFA, onboarding, organization picker, provider status, or payment report UI | Extend existing pages and hooks; add only the missing routes and components listed below |
| Billing | Stripe checkout, plans, subscriptions, usage limits | Plans are USD-priced; checkout has no GBP/USD region selection; account eligibility unverified | Keep Stripe for subscriptions only; add region-aware prices after external verification; do not block AP on billing |
| Caching | Org-scoped React Query keys, `no-store` BFF session, org-scoped Redis keys | Existing AP hook comment says workspace switch never clears cache, which conflicts with the roadmap; post-mutation invalidation is inconsistent | Fix query lifecycle in the existing hooks; keep the existing key convention |

### 5.2 Provider capability matrix

This is the contract the adapters must satisfy. "Verified" means proven in the provider's test environment (Xero/QuickBooks sandbox or Sage trial business) and recorded in the implementation notes; "expected" means documented but not yet proven. Do not treat an expected cell as launch evidence.

| Capability | Xero | QuickBooks Online | Sage Accounting (required MVP — verify) | Manual / no connection |
|---|---|---|---|---|
| Connection | OAuth 2.0 authorization code; refresh token; tenant header (`xero-tenant-id`) | OAuth 2.0; realm ID identifies the company; refresh token | OAuth 2.0 authorization code; exact authorize/token endpoints, scopes, regional base URL, and any business-selection header or parameter must be read from official documentation and the registered app | None |
| Business/organization selection | `GET /connections` returns authorized tenants; admin must choose one | Realm comes from the OAuth callback; show company name; multiple companies require separate authorization | Use the **User Accounts** resource area to identify businesses the authorized user can access; admin must choose one and persist its external ID, name, and region. Do not auto-select | Not applicable |
| Identity stored | `tenant_id`, tenant name, connection status | `realm_id`, company name, connection status | External business ID, business name, region, connection status; field names confirmed during verification | None |
| Supplier matching | Contacts API; map by `ContactID`, then normalized name/email | Existing vendor sync; map by `Id`/`DisplayName` | **Contacts** resource area; map by external contact ID, then normalized supplier name. Import only supplier-matching fields; do not import unnecessary personal or bank details | Manual vendor create/edit |
| Chart-of-accounts sync | Accounts API; map by account ID/code; only active postable accounts selectable | Existing `QuickBooksChartOfAccountsSync`; reuse | **Chart of Accounts** resource area; map by external ID/code; keep only active postable accounts. Confirm account types and status fields | Seed starter COA |
| Purchase transactions | `POST /Invoices` with `Type: ACCPAY` for supplier bills | Existing `create_bill` on the Bill entity | **Purchase Transactions** resource area: create/update approved supplier invoices; read for reconciliation. Field and endpoint names confirmed in verification | Not applicable |
| Credit notes | Supplier credit-note creation only where verified | Existing credit-note support if verified | Create/update relevant supplier credit notes through **Purchase Transactions** only if the verified API and app permission allow it; otherwise keep credits local and visible | Local credit records |
| Status codes and types | Invoice status/type fields read from the API | Bill status/type fields read from the API | **Status Codes & Types** resource area read-only; use to interpret transaction type and status. Do not write custom statuses | Local states |
| Currency | Multi-currency if enabled on the Xero organization; `CurrencyCode` per invoice; base currency constraints | Multi-currency if enabled; `CurrencyRef`; home currency otherwise | **Currencies** resource area read-only: confirm supported currencies and whether an exchange rate is required. Never convert silently | Invoice currency preserved locally; no posting |
| Taxes | Existing tax-mapping model supports Xero tax types; verify per tenant | Existing tax mapping; verify per realm | **Taxes** resource area read-only: read and map existing tax references. Do not determine tax treatment, calculate tax, or file returns | No provider mapping |
| Settings | Organisation settings read for currency/account configuration | Company preferences read for currency/account configuration | **Relevant Settings** read-only: only the business and accounting configuration needed by the integration. Do not read unrelated company data | Not applicable |
| Attachments | Optional support if a customer workflow needs the source file in Xero | Optional support if verified | Optional and **not in the first slice**. Add only if a verified Attachments capability is required for a useful customer workflow and can be scoped without broadening the integration | Original file retained in InvoiAI |
| Purchase-order sync | Purchase Orders API; Xero remains PO source of truth | Existing PO sync if verified; confirm coverage before claiming | **Not in the agreed Sage AP scope.** Use manual/CSV POs and disclose the limitation. Do not add Products & Services, Opening Balances, or Reporting to compensate | Manual/CSV POs |
| Goods receipts | No receipt object; captured in InvoiAI | No receipt object; captured in InvoiAI | No receipt object in scope; captured in InvoiAI | Manual/CSV receipts |
| Idempotency | Do not assume a provider key; local `erp_sync_key` plus pre-flight reconciliation | Do not assume a provider key; local `erp_sync_key` plus pre-flight reconciliation | Do not assume a provider key; local `erp_sync_key` plus pre-flight query by contact and reference, then compare amount/date/currency | Local uniqueness only |
| Rate limiting | Per-tenant limits; honor `Retry-After` | Per-realm limits; honor `Retry-After` | Per-business limits; confirm headers and limits; honor `Retry-After` where provided | Not applicable |
| Failure visibility | 401/403 reconnect; 429 backoff; 4xx stop; 5xx/timeout retry | 401/403 reconnect; 429 backoff; 4xx stop; 5xx/timeout retry | 401/403 reconnect; 429 backoff; 4xx stop; 5xx/timeout retry. Record safe error codes; never expose provider payloads | Manual review only |
| Launch risk | Medium: tenant picker and POST write are missing | Medium: existing code is reusable but currency and duplicate behavior are unverified | Medium–high: no code exists, and the product/version, regional endpoints, auth, and resource shapes are unverified. The scope is fixed, so the risk is delivery effort, not scope ambiguity | Low: partially works; must be made explicit |

### 5.3 Currency behavior matrix

The workspace currency is the default for limits, display, and exports. The invoice currency is always the supplier's currency. The provider posting rule is evaluated before any write.

| Scenario | Workspace default | Invoice currency | Provider posting rule | MVP behavior |
|---|---|---|---|---|
| UK customer, UK supplier | GBP | GBP | Post in GBP if the provider organization’s base/home currency is GBP | Auto-post after approval and coding. |
| US customer, US supplier | USD | USD | Post in USD if the provider organization’s base/home currency is USD | Auto-post after approval and coding. |
| UK customer, US/EU supplier | GBP | USD or EUR | Post in the invoice currency only if multi-currency is enabled and that currency is active/configured | Auto-post only after provider evidence (Xero/QuickBooks sandbox or Sage trial business); otherwise mark `currency review required` and keep manual export. |
| US customer, UK/EU supplier | USD | GBP or EUR | Same as above | Same as above. |
| Nigerian or other customer | NGN or selected ISO | NGN or other | Post only if the provider supports the currency, the organization is configured for it, and provider evidence covers it (Xero/QuickBooks sandbox or Sage trial business) | Preserve NGN; allow manual AP, approval, and export even when posting is unavailable; do not claim NGN localization. |
| Provider multi-currency disabled | Any | Foreign | Cannot post the foreign currency | Block auto-post with a clear reason; keep the invoice approved and exportable. |
| Provider currency not enabled/configured | Any | Foreign | Cannot post until an administrator enables the currency in the provider | Block auto-post; show the exact provider action required; keep manual AP available. |
| Provider requires an exchange rate | Any | Foreign | Requires a rate or provider-side conversion | Do not guess. Require a human-entered/confirmed rate, record source and actor, and only then allow a retry. Defer automatic FX rate lookup. |
| Provider rejects the currency at POST | Any | Any | 4xx validation error | Stop retrying, set `erp_currency_status = rejected`, show the provider message in safe form, keep manual AP available. |
| No accounting connection | Any | Any | No posting | Store the invoice, approve it, export payment instructions, and record customer-reported status. |

**Hard rules**

- Never change the stored invoice amount or currency to the workspace currency.
- Never infer an exchange rate from a display conversion.
- A conversion shown for limit comparison is not a posting rate and must be labelled as such.
- If the provider cannot post the currency, the invoice remains `APPROVED` in InvoiAI with `erp_sync_status = blocked_currency`; it is not silently downgraded or deleted.
- Payment-instruction export does not depend on provider posting.
- For Sage, the **Currencies** resource area is read before any Purchase Transactions write to learn whether the business supports the currency and whether a rate is required. The exact read shape and rate semantics must be confirmed during verification.

### 5.4 Requirement-to-seam matrix

This table is the compact implementation contract for each workstream. Details follow in the numbered sections.

| Requirement | Reusable now | Gap | Smallest seam | Primary routes | Models/schemas | Worker | Focused verification |
|---|---|---|---|---|---|---|---|
| Signup, OTP, Google, MFA, sessions | Supabase email/password auth, BFF cookie, `AuthUser.is_verified`, reset/logout | First/surname fields, six-digit OTP, Google identity, MFA, recovery codes, verification gate, optional mobile | Extend auth repository/service; add verification and MFA services; verified-user dependency; keep email as primary path | `/auth/signup`, `/auth/verify-otp`, `/auth/resend-otp`, `/auth/google/*`, `/auth/mfa/*` | OTP challenge, recovery codes, auth request/response schemas, `AuthUser` assurance | None; request-path services | OTP expiry/attempts, Google state/nonce, MFA AAL2, unverified 403, NG signup without SMS |
| Business onboarding and workspace | Workspace creation, owner membership, settings, switcher | Resumable onboarding, business type/registration status, industry, volume, accounting software, approver assignment, seat-impact preview, complete flag, market-aware currency default | Extend `WorkspaceCreate` and organization creation; add onboarding draft/complete router | `/onboarding`, `/onboarding/complete`, `/organizations/{id}/profile`, `/workspaces` | Organization onboarding fields, membership business role, onboarding draft | None | Optional skip, atomic create, owner role, resume, edit later, NG signup allowed, no company/tax ID required |
| Pricing, seats, trial, and billing | Plan catalog, Stripe service, subscription fields, `seat_limit_for` (unused) | Trial state, invoice allowance, included/used/pending seats, seat enforcement, per-seat add-on, GBP/USD prices, no free tier | Extend plan catalog and billing router; enforce seats in invite/accept; Stripe quantity/trial; add seat-usage and allowance endpoints | `/billing/plans`, `/billing/checkout`, `/billing/subscription`, `/billing/seats`, `/billing/trial` | Plan/price/seat catalog, seat usage, trial state, allowance counters | Billing webhook processor | Unique-member seat count, invite blocked at limit, allowance separate from seats, trial end state, GBP/USD display |
| Upload and forwarding email | Upload service, SHA-256 hashing, storage, duplicate error, email intake, idempotent attachments, HMAC webhook | SPF/DKIM/DMARC, quarantine, malware scanning, cross-channel dedupe, rate limits | Extend upload and email services; add auth/scan fields to intake records | `/documents`, `/documents/batch`, `/ap/email-address`, `/ap/email/inbound` | Intake event auth/scan fields, duplicate fingerprint | `OCRWorker` starts after acceptance | Signature/replay, quarantine, malware, duplicate, batch partial success |
| Extraction, validation, evidence | OCR worker, extraction engine, analysis worker, verification engine, line items | Consistent confidence/evidence payload; complete line-item contract; deterministic anomaly output | Extend analysis output and review payload; keep worker chain | `/documents/{id}/capture`, `/documents/{id}/analyze`, `/documents/{id}/workflow` | Analysis/extraction evidence fields, line-item contracts | `OCRWorker`, `AnalysisWorker` | Arithmetic, dates, currency, evidence immutability, decimal totals |
| Duplicate and anomaly review | Duplicate checker, verification engine, exception repository, review UI | Cross-channel duplicate candidate reasons; one review queue | Extend existing duplicate check and exception service | `/ap/exceptions`, `/ap/exceptions/{document_id}`, resolve/waive | `invoice_exceptions`, duplicate evidence | Matching/analysis workers create exceptions | Exact and fuzzy duplicates, never auto-delete, waiver audit |
| Supplier and GL coding | Vendor service/sync, external IDs, COA service/cache, coding rules, GL coding service | Provider-neutral supplier/COA import; active-account enforcement; manual fallback when no provider or resource is available | Provider dispatch in COA/vendor services; keep GL service | `/vendors`, `/ap/chart-of-accounts/sync`, `/ap/codings/*`, `/ap/coding-rules` | Vendor external IDs, COA external IDs, coding source/status | `APCodingWorker` | Idempotent imports, inactive account blocked, rule precedence, coding approval |
| PO, receipt, matching | PO/receipt routes and repositories, matching service, tolerances, exceptions | Persisted multi-PO line allocation; partial accumulation; PO-change flag; provider PO capability flag | Add allocation table/repository; extend matching service | `/purchase-orders`, `/goods-receipts`, `/ap/matching/*`, `/ap/documents/{id}/run` | Allocation table, PO/receipt lines, tolerance settings | `APMatchingWorker` | Two/three-way, partials, over-allocation, tolerance boundaries, no auto-approval |
| Approval, limits, SoD, reapproval | Approval engine, routing, authority, SoD, delegations, history | Configurable self-approval threshold, FX-at-invoice-date, critical-field revocation end to end | Extend approval engine/bridge; no second workflow | `/approvals`, `/ap/rules`, `/organization-access/*` | Workflow/step/history, authority, currency snapshot | `ApprovalWorker` | Limit enforcement, self-approval, FX flag, revocation, escalation |
| Accounting connection lifecycle | Partial `IntegrationService`, encrypted tokens, QuickBooks and Xero OAuth | No provider-neutral organization selection; Xero auto-selects first tenant; no Sage connector; no unified status | Extend `IntegrationService` and provider factory; add organization-list/select methods | `/integrations`, `/integrations/{provider}/connect`, `/callback`, `/organizations`, `/organization` | `integration_connections` external org fields, status/error, audit | Provider sync workers | No auto-select, one active connection, reconnect, switch confirmation, MFA |
| QuickBooks write-back | `QuickBooksAccountingProvider`, `BillSyncService`, `BillSyncWorker`, QBO client | Hardcoded provider and USD default; duplicate protection unaudited; currency not passed | Reuse adapter; make worker provider-neutral; audit duplicates; map currency | `/ap/documents/{id}/create-bill`, `/retry-bill-sync`, `/status` | `erp_provider`, `erp_sync_key`, attempts/errors, currency status | `BillSyncWorker` | No pre-approval POST, one POST, timeout adopt, 5xx retry, 4xx stop, GBP/USD/NGN behavior |
| Xero write-back | Xero OAuth, tokens, inbound sync classes, `XeroWorker` | Tenant picker, POST/PUT client, provider adapter, imports, reconciliation | Add `XeroAccountingProvider`; extend client/sync | Same bill routes + `/integrations/xero/*` | Tenant selection, `erp_sync_key`, external IDs | `BillSyncWorker`, `XeroWorker` | Tenant header, ACCPAY payload, one POST, timeout adopt, currency gate |
| Sage AP write-back | Enum/domain references only | No OAuth, client, or adapter; product/version, region, authorization, and resource shapes unverified | Complete the verification in 5.5; then add a Sage Accounting API 3.1 client/adapter scoped to the agreed AP resource areas | `/integrations/sage/*` + bill routes | External business ID, region, external IDs, status/tax/currency references | `BillSyncWorker`, `SageWorker` | Sage trial-business evidence; business selection, contacts, COA, purchase transactions, status codes, currencies, taxes; one POST; retry/duplicate; no excluded resource calls |
| Payment CSV/PDF and status | Payment instruction/events, authorization queue, export buttons | Batch export, PDF, append-only customer-reported status | Add export service and status-report table/routes | `/ap/payments/export`, `/ap/payments/{id}/status-reports` | Payment instruction/events, status reports | Existing payment workers; none for export | CSV safety/precision, tenant scope, PDF totals, report idempotency/label |
| Frontend and caching | App Router, React Query, RHF, Zod, Radix, AP pages/components | OTP/Google/MFA/onboarding/provider-organization/sync/export/status surfaces; switch-cache conflict | Extend existing pages/hooks; fix invalidation and clearing | All above | Client types mirroring API schemas | None | E2E happy path, manual no-connection path, cache clear, accessible states |

### 5.5 Sage Accounting AP scope and verification — required before implementation

**Decision**

Sage Accounting is a required MVP provider. It is not deferred, optional, or awaiting a product-family decision. Sage Intacct, Sage 50/50cloud, Sage 100, Sage X3, and Sage Active are not MVP targets. The product target is **Sage Business Cloud Accounting API 3.1**. The connector is limited to the resource areas below and is built only after the exact product/edition/version, regional availability, authorization, endpoints, and field shapes are verified in official documentation and a **Sage trial business account**.

Sage Business Cloud Accounting API has **no development sandbox**. Do not require or claim a Sage sandbox. All Sage read/write evidence comes from a Sage trial business account using API 3.1. Xero and QuickBooks Online keep their sandbox requirements.

The names below are **API resource areas, not confirmed OAuth permission scopes**. Do not treat a resource-area name as a scope string, endpoint path, or permission grant. Read the actual scopes from the registered app and official documentation.

**Resource-area contract**

| Resource area | Why InvoiAI needs it | Allowed use in the MVP | Explicit limit |
|---|---|---|---|
| User Accounts | Identify the businesses the authorized user can access | List accessible businesses after authorization; the administrator selects exactly one; persist external business ID, name, and region | No user administration, invitations, role changes, or employee data |
| Contacts | Supplier matching | Read supplier contacts; map by external ID, then normalized supplier name. Store only fields needed for matching and coding | Do not import or sync unnecessary personal details, bank details, or customer records |
| Chart of Accounts | Account selection and GL coding | Read active postable accounts; map by external ID/code; show last sync and per-account status | No account creation, edits, opening balances, or ledger postings |
| Purchase Transactions | Approved supplier invoices and relevant credit notes | Create/update one approved purchase invoice at a time; read it back for reconciliation; create/update relevant supplier credit notes only if verified | No sales transactions, payments, receipts, journals, or bulk posting |
| Status Codes & Types | Interpret transaction type and status | Read-only: display the provider status/type and use it for reconciliation and next-action logic | Do not create or mutate custom statuses or types |
| Currencies | Check supported currencies and exchange-rate requirements | Read-only before any write: supported, rate required, or unsupported | Never convert silently; never infer a rate; no automatic FX lookup |
| Taxes | Read and map existing tax references | Read-only: map an existing provider tax reference to the invoice line | Do not determine tax treatment, calculate tax, file returns, or create tax codes |
| Relevant Settings | Read business and accounting configuration needed by the integration | Read-only: only settings that affect business identity, currency, account posting, or capabilities | Do not read or store unrelated company configuration |
| Attachments | Optional copy of the source invoice file into Sage | **Not in the first slice.** Add only if a verified capability is required for a useful customer workflow and can be scoped without broadening the integration | No bulk file sync, no retention outside the provider's policy, no attachment-based automation |

**Explicit exclusions**

Do not add, call, or plan any of the following:

- Sage Banking, bank feeds, or bank-account access.
- Payments & Receipts, payment initiation, supplier payments, or settlement.
- General journal, ledger entries, or manual double-entry operations.
- Sales Transactions, customer invoices, or receivables.
- Opening Balances.
- Products & Services or inventory.
- Reporting, report builder, or financial statements.
- Any user/employee administration beyond identifying accessible businesses.
- Any tax determination, tax filing, or e-invoicing/fiscalization.

**Verification required before implementation**

1. Obtain a Sage developer/partner account, register the app, and record redirect URIs and app-review requirements.
2. Confirm the exact product, edition/version, supported countries, and regional base URL/token endpoints from official documentation for **Sage Business Cloud Accounting API 3.1**.
3. Confirm whether the exact **Sage Start** edition supports supplier purchase transactions before presenting it as AP-compatible.
4. Confirm the authorization flow, scopes/permissions, token lifetime/refresh, and the business-selection header or parameter.
5. Confirm the User Accounts response and how to list businesses the authorized user can access.
6. Confirm Contacts fields and how to distinguish suppliers from customers without importing unnecessary personal or bank data.
7. Confirm Chart of Accounts fields, account types, active/inactive state, and which accounts are postable.
8. Confirm Purchase Transactions create/update/read fields for supplier invoices and relevant credit notes.
9. Confirm Status Codes & Types values and how they map to local sync states.
10. Confirm Currencies read shape, supported-currency behavior, and exchange-rate requirements for GBP, USD, and NGN.
11. Confirm Taxes read shape and how an existing tax reference attaches to a line.
12. Confirm relevant Settings fields and whether any are required before a write.
13. Confirm Attachments support and limits; decide explicitly whether to include them later.
14. Confirm rate limits, error format, timeout behavior, webhook support (if any), and trial-business data setup. Sage has no development sandbox.
15. Prove one approved purchase invoice in the Sage trial business account with idempotent retry, timeout reconciliation, and duplicate prevention.
16. Prove that no excluded resource is called by the adapter, including negative tests.
17. Record the evidence as a short ADR and in the Sage trial-business evidence log.

**If a capability cannot be verified**

- Keep Sage in the MVP. Do not silently drop it or replace it with another Sage product.
- Narrow the Sage claim to what was verified; record the limitation in the integrations UI and acceptance criteria.
- Keep manual AP available for the affected invoices.
- Do not call a broader endpoint as a workaround, and do not infer a field contract from a different Sage product.
- Do not mark the Sage slice launch-ready until the trial-business evidence exists.
- Do not use Sage Active, Sage 50, Sage 100, Sage Intacct, or Sage X3 as substitutes.
- Do not describe a Sage development sandbox; Sage Business Cloud Accounting API does not provide one.

**What not to do**

- Do not build a “generic Sage” adapter or a connector for Intacct, Sage 50, Sage 100, or Sage X3.
- Do not treat resource-area names as confirmed scopes.
- Do not claim purchase-order sync, attachments, multi-currency, or NGN support before trial-business evidence.
- Do not add Banking, Payments & Receipts, journals, Sales, Opening Balances, Products & Services, or Reporting as a workaround for a missing field.
- Do not use a Sage development sandbox, Sage Active, Sage 50, Sage 100, or Intacct.
- Do not remove Sage from the MVP because verification is inconvenient.

### 5.6 Pricing, seats, trial, and entitlement contract

**Decision status**

The product direction is confirmed: plans bundle a monthly workspace invoice allowance with included user seats; seats and allowances are separate; there is no permanent free tier. **Approved on 2026-11-08:** the Solo/Duo/Team seat structure, unique-member counting, separate invoice allowance, and the 14-day/25-invoice/no-card trial with read-only plus export at the end. **Still unapproved:** final GBP/USD prices, monthly invoice allowances, additional-seat rate, and proration. Checkout stays gated until those values are approved.

**Approved starting structure**

| Plan | Included seats | Intended use | Invoice allowance |
|---|---|---|---|
| **Solo** | 1 (owner) | Sole practitioner | Owner-approved amount |
| **Duo** | 2 (owner + reviewer/approver) | Owner plus one reviewer/approver | Owner-approved amount |
| **Team** | 5 | Small finance team | Owner-approved amount |

- Additional seats are a paid add-on at the plan's per-seat rate.
- Keep GBP plans for UK workspaces and USD plans for US workspaces. Nigeria billing and Stripe eligibility are a separate verification item.
- This structure is the simplest that satisfies the one-user, two-user, and small-team requirement without inventing a fourth tier.

**Seat counting rules**

- One seat is one unique active workspace membership. Multiple roles on the same member never consume more than one seat.
- Pending invitations, revoked invitations, removed members, and disabled members do not consume a seat.
- The creator's owner membership counts as one seat.
- Seat usage is calculated from active memberships, not from profile rows or role assignments.
- Seat enforcement runs server-side when an invitation is created or accepted and when a member is reactivated. The frontend warning is not the control.
- An invitation that would exceed the seat limit is blocked with `SEAT_LIMIT_REACHED` unless the owner first adds seats or removes access.
- Changing a member's role never changes the seat count.
- Seat usage does not count across workspaces; each workspace has its own subscription and seat count.
- If a workspace is downgraded below its active member count, existing members keep access but no new invitations are allowed until the count fits or seats are added. Do not silently remove members.

**Seat usage surface**

`GET /api/v2/billing/seats` returns `included`, `used`, `pending`, `available`, `additional_seat_rate`, `currency`, and `next_charge_estimate`. The UI shows this as one `SeatMeter` line: “3 of 5 seats used · 1 pending · add seats”. The invite dialog reads the same endpoint before allowing a send.

**Invoice allowance rules**

- The allowance counts documents entering the AP pipeline per billing period. It does not count approvals, exports, supplier-payment instructions, sync attempts, or teammate activity.
- At 80% and 100%, show a persistent warning. At 100%, pause only new AI/OCR extraction. Manual creation/editing, review, approval, accounting sync, export, and existing records continue.
- No surprise overage charge and no lockout. The owner chooses to upgrade or wait for the period reset.
- The allowance is independent of the seat count: adding seats never increases the invoice allowance, and upgrading the allowance never adds seats.

**Trial rules (approved 2026-11-08)**

- Duration: 14 days.
- Invoice cap: 25 processed invoices.
- Card at signup: not required.
- End without a chosen plan: read-only access plus export; no new intake or AI processing.
- End with a chosen plan: normal paid access.
- One trial per workspace. Do not allow repeated trials by creating workspaces to reset the cap.
- Show `TrialBanner` with days left, invoices used against the cap, and the exact end behavior.
- A trial is not a permanent free plan. Do not seed a Free price ID or a Free plan card.

**Billing data contract**

- `plan`, `billing_interval`, `currency`, `price_id`, `included_seats`, `invoice_allowance`, `additional_seat_rate`.
- `subscription.status` distinguishes `trialing`, `active`, `past_due`, `canceled`, and `read_only_after_trial`.
- `trial_start`, `trial_end`, `trial_invoice_cap`, `trial_invoices_used`.
- Stripe checkout sends the seat quantity and the correct currency price; it does not hardcode quantity 1.
- Stripe is used for InvoiAI subscription billing only. It is not connected to supplier payments.

### 5.7 Signup and business-onboarding flow

**Two-stage shape**

1. **Account registration (`/signup`):** first name, surname, business email, password or Google. Mobile is optional here. No company registration number, tax ID, or card.
2. **Email verification:** six-digit email OTP (the roadmap target). The current link-based flow is a gap to close.
3. **Business onboarding (`/onboarding`):** a resumable wizard that creates the first workspace on completion. The creator becomes owner/admin.

Do not merge stages 1 and 3 into one long form.

**Field classification**

| Field | Stage | Requirement | Notes |
|---|---|---|---|
| First name | Registration | Required | Trim, 1–60 characters |
| Surname | Registration | Required | Trim, 1–60 characters |
| Business email | Registration | Required | Verified by email OTP |
| Password or Google | Registration | One required | Password minimum 8; Google uses server-side code flow |
| Mobile with country code | Registration or onboarding | Optional | E.164; used for recovery/notifications; never blocks signup |
| Workspace/business name | Onboarding | Required | 2–120 characters |
| Country | Onboarding | Required | Defaults currency/format; not tax |
| Default currency | Onboarding | Required with override | UK→GBP, US→USD, NG→NGN suggested; all editable |
| Accounting software | Onboarding | Required answer, including “none”/“not sure” | Xero, QuickBooks Online, Sage Accounting, none, not sure |
| Business type / registration status | Onboarding | Required answer, including “not yet registered” | Never require a company number |
| Industry | Onboarding | Required from closed list + “other” | Editable later |
| Team size | Onboarding | Required band | Drives seat recommendation |
| Monthly invoice volume | Onboarding | Required band | Drives allowance recommendation |
| Invite teammates + roles | Onboarding | Optional | Workspace Admin, Invoice Reviewer, Approver; shows seat impact |
| Assign approver | Onboarding | Optional | Can be completed before first invoice |
| Referral code | Omitted at launch | Not collected | Omit unless an existing launch purpose is confirmed |
| Company registration number | Deferred | Optional | Only when billing/accounting setup justifies it |
| Tax ID / VAT number | Deferred | Optional | Only when billing or a specific accounting setup requires it; never for account/trial/manual AP |

**Verification sequence**

- Primary: email OTP with the policy in section 2 (Identity and authentication): six digits, ten-minute expiry, five attempts, sixty-second resend, five sends/hour, single use, non-enumerating.
- Link-based verification may be supported as an alternative entry point during migration, but the target is OTP.
- SMS OTP is **optional**. Evaluate it as a recovery or second factor, not a mandatory parallel step. Compare provider cost, country coverage (especially Nigeria), latency, and friction before adoption.
- If SMS is adopted, a user who cannot receive it must still verify by email and complete signup and manual AP.
- Do not require email and SMS OTP together without a recorded reason.
- Mobile number collection must not imply SMS verification.

**Resumability**

- Persist onboarding answers as a draft keyed to the user and workspace intent.
- `GET /onboarding` returns completed steps, the next step, and the saved draft.
- The user can leave after any step and resume on the same step.
- Completing onboarding is idempotent; retrying does not create a second workspace.
- Skipped optional fields are recorded as intentionally skipped where the distinction matters.

**Tax boundary**

Country selection sets display defaults only. It does not create a tax registration, decide tax treatment, or file anything. Tax choices and accounting mappings remain explicit user decisions.

**Sage edition clarity**

During connection setup, show the exact supported Sage Accounting product/edition. Do not show “Sage Accounting Start (Quotes & Invoicing Only)” as AP-compatible unless a Sage trial business account and official documentation verify supplier purchase-transaction support. If an edition is not supported, explain why and keep manual AP available.

### 5.8 Frontend design direction

**Skill use**

- Use **UI/UX Pro Max** for the authenticated product: navigation, tables, forms, review, approval, settings, billing, and onboarding.
- Use **Scroll Craft** for the public landing and pricing journey only. Do not force scroll-driven storytelling into the authenticated AP workflow.

**Visual language**

- Premium, distinctive, polished. Restrained glass surfaces, glossy color accents, and a few dimensional moments.
- Smooth, purposeful transitions of roughly 150–250 ms; no decorative motion that competes with work.
- Lottie only for meaningful onboarding, success, or empty states. Not for every icon, table row, approval, or money value.
- Keep invoice tables, forms, review, and approval screens high-contrast, calm, fast, and easy to scan. Do not place blur or glass behind dense text or financial values.
- Reuse the implemented DM Sans (UI) and Playfair Display (display) pairing. Do not introduce new fonts without a design review.
- Consolidate the competing `:root` token blocks in `globals.css` into one semantic layer (surface, ink, muted, accent, border, danger, focus, radius, elevation, motion).

**Accessibility and performance**

- Keyboard access, visible focus, labelled fields, screen-reader status text, and reduced-motion support.
- Responsive mobile layouts for onboarding, review, approval, and billing.
- No new 3D or animation dependency without a specific need. Reuse the existing Next.js, Tailwind, Radix, Lucide, React Query, React Hook Form, and Zod stack.
- Replace or remove remote Lottie iframes; use local, licensed, lazy-loaded assets or none.
- Keep the authenticated app fast; public scroll effects must not ship in the dashboard bundle.

**Public versus product surfaces**

| Surface | Direction |
|---|---|
| Public landing/pricing | Scroll Craft storytelling, glass/gloss accents, dimensional hero, live plan catalog, trial CTA, no permanent-free claim |
| Signup/verification | Calm, short, high-contrast; one meaningful Lottie at most |
| Onboarding | Resumable steps, progress indicator, clear skip, seat-impact preview |
| Dashboard, tables, review, approval | High-contrast, dense-but-calm, minimal motion, no glass behind values |
| Billing | SeatMeter, AllowanceMeter, TrialBanner, currency-correct prices |

### 1. Foundation and evidence

- Make `backend/migrations/` the only migration authority. Fix the manifest text that points at `app/migrations`. Reconcile every migration against staging before adding new ones.
- Fix test collection before feature work: install declared dependencies (`slowapi`, `pytest-asyncio`), keep `asyncio_mode = auto`, and pin the CI runtime. A local unpinned run is not acceptance evidence.
- Enable RLS on every tenant-owned table used by this spec, with a membership policy based on `org_members`. Keep service-role access for workers, but every worker must derive `org_id` from the record, not from the job payload.
- Add private storage, signed download expiry, quarantine, attachment scanning, backup/restore verification, and alerting as launch gates.
- Add organization-scoped audit indexes and a migration/backout runbook.
- Create a provider evidence matrix before provider work: Xero demo company and QuickBooks sandbox company, plus a Sage trial business account using API 3.1. Sage has no development sandbox. No provider feature is “done” from mocked calls alone.
- Add a provider-contract test harness in CI so Xero, QuickBooks, and Sage adapters are exercised against the same behavioral assertions.
- Record the current QuickBooks duplicate behavior in a short audit note before changing it. The audit must state what happens on timeout, retry, and concurrent workers.

### 2. Identity and authentication

**Data and contracts**

- Signup request gains `first_name`, `last_name`, and an optional `mobile` (E.164 with country code). Email remains the business email. Store names in Supabase user metadata and in the local profile used by the app.
- The current `/signup` form collects email and password only and verification is link-based. Close that gap: the target is a short registration form plus six-digit email OTP.
- `AuthUser` gains an optional display name, an optional verified mobile, and an assurance level (`aal1` or `aal2`) derived from the validated token.
- Add an OTP challenge record for attempt/resend enforcement. Store a hash of the code, never the code itself. If Supabase generates the OTP, still track the send window and failed-attempt count locally.
- Add hashed, single-use MFA recovery codes. Never return the plaintext more than once.
- Add `onboarding_completed_at` and `onboarding_version` to the organization, not to the auth user.

**OTP policy**

- Six digits by email.
- Ten-minute expiry.
- Five verification attempts per code.
- Sixty-second resend cooldown.
- Maximum five sends per hour per email and per IP.
- Single use; a successful verification invalidates the code.
- Non-enumerating responses: the resend endpoint always reports that a code was sent if the request is accepted.
- OTPs are never written to logs, analytics, client storage, or Redis.
- Email OTP is the primary path. SMS OTP is not required; if added, it is an optional recovery or second factor and must not block users in Nigeria or anywhere SMS is unavailable.

**Google OAuth**

- Use the server-side authorization-code flow. The backend exchanges the code and creates the encrypted BFF session. Provider tokens never reach browser storage or the frontend.
- Use a distinct auth callback route; do not reuse the integration callback used for accounting providers.
- Link an existing account only when the provider reports a verified email. Otherwise create a new account and require verification. Never silently merge accounts.
- Store state and nonce server-side or in a short-lived signed cookie; validate both on callback.
- Treat a cancelled or denied consent as a normal user-facing outcome, not a server error.

**MFA**

- TOTP authenticator app for owners and administrators, separate from email verification.
- Recovery codes: ten single-use codes, hashed at rest, shown once, regenerable.
- After password or Google login, an owner/admin without a verified TOTP factor is placed in a restricted MFA-enrollment state. They may reach only MFA setup, logout, and support.
- An owner/admin with a factor must satisfy an AAL2 challenge before organization settings, member/role changes, accounting connect/reconnect/switch, exports, and any future bank-detail action.
- Enforce AAL2 server-side on the protected routes. Do not rely on the frontend to hide buttons.
- If an organization has no owner/admin with MFA after a grace period, block new pilot onboarding rather than silently downgrading security.

**Sessions and verification**

- Keep the encrypted httpOnly BFF session cookie.
- Access token: one hour. Refresh token: 30 days. Rotate refresh tokens.
- Revoke sessions on logout, password change/reset, and membership removal.
- Every protected business router depends on a verified user plus an active membership. `src/proxy.ts` remains a coarse redirect filter only.
- A user with no workspace is routed to onboarding, not to the dashboard.
- A user with a workspace but incomplete onboarding is routed to the onboarding wizard.
- Password reset uses a single-use, expiring token. Reset does not reveal whether the email exists.
- Rate-limit login, signup, OTP send, OTP verify, password reset, and Google callback.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/v2/auth/signup` | First name, surname, email, password, optional mobile; returns verification requirement |
| POST | `/api/v2/auth/verify-otp` | Verify six-digit code and establish a session |
| POST | `/api/v2/auth/resend-otp` | Resend with cooldown and non-enumerating response |
| GET | `/api/v2/auth/google/authorize` | Start server-side Google authorization |
| GET | `/api/v2/auth/google/callback` | Exchange code, link/create user, set BFF session |
| POST | `/api/v2/auth/login` | Email/password login |
| POST | `/api/v2/auth/refresh` | Rotate the session |
| POST | `/api/v2/auth/logout` | Revoke and clear the session |
| POST | `/api/v2/auth/forgot-password` | Non-enumerating reset request |
| POST | `/api/v2/auth/reset-password` | Consume reset token and set a new password |
| GET | `/api/v2/auth/me` | Current identity, verification, assurance level, memberships |
| POST | `/api/v2/auth/mfa/enroll` | Create a TOTP factor |
| POST | `/api/v2/auth/mfa/verify` | Confirm factor enrollment and return recovery codes once |
| POST | `/api/v2/auth/mfa/challenge` | Start an AAL2 challenge |
| POST | `/api/v2/auth/mfa/recovery` | Consume a recovery code |
| GET | `/api/v2/auth/mfa/factors` | List factors without secrets |
| DELETE | `/api/v2/auth/mfa/factors/{id}` | Remove a factor after step-up |

### 3. Onboarding and workspace model

**Model**

- Keep identity, membership, and business data separate.
- Organization fields: name, country, currency, industry, company-size band, monthly supplier-invoice-volume band, business type/registration status, accounting-software choice, optional referral code, onboarding completion timestamp/version.
- Membership fields: organization, user, role, active state, business role/job title, approval limits. The creator receives `owner`.
- Do not store a second role system. Use the existing role/permission layer, but expose the three AP roles in the invite UI: **Workspace Admin**, **Invoice Reviewer**, and **Approver**.
- Onboarding answers are editable later. Optional questions are skippable and recorded as intentionally skipped where that distinction matters.
- Never require a company registration number or tax ID to create an account, start a trial, or use manual AP. If collected later for billing or a specific accounting setup, keep it optional until a recorded requirement exists.
- Store onboarding answers as a resumable draft until completion, then create the workspace atomically.

**Creation rule**

The first business workspace is created atomically with the owner membership, organization settings, and usage row. The existing creation method already compensates on failure; keep that behavior.

**Market-aware currency default**

- `GB` → `GBP`
- `US` → `USD`
- `NG` → `NGN` as a suggested default, editable
- Other countries → the user selects an ISO 4217 currency; do not leave it empty and do not block signup for lack of a default.

The default is a convenience, not a restriction. A UK workspace may use USD if the business operates that way; an NGN workspace is not blocked from the AP workflow.

**Route contract**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/onboarding` | Return completed steps, next step, and any resumable draft |
| PATCH | `/api/v2/onboarding/draft` | Save one step without completing onboarding |
| POST | `/api/v2/onboarding/complete` | Validate answers, create the first workspace/owner membership, apply the approved trial |
| PATCH | `/api/v2/organizations/{id}/profile` | Edit business profile later |
| GET | `/api/v2/workspaces` | List workspaces for the current user |
| POST | `/api/v2/workspaces` | Create a subsequent workspace with the same validated fields |

**Validation**

- First name and surname: 1–60 characters, trimmed.
- Business name: 2–120 characters, trimmed.
- Country: ISO 3166-1 alpha-2. Do not restrict to UK/US.
- Currency: ISO 4217. UK defaults to GBP, US to USD, Nigeria may default to NGN; all are editable.
- Industry: closed list plus an “other” option with a short free-text description.
- Team size and invoice volume: closed bands, not free text.
- Accounting software: Xero, QuickBooks Online, Sage Accounting, none, or not sure. None and not sure are valid and must not block onboarding.
- Business type/registration status: closed list including “not yet registered”.
- Invitations: optional, with Workspace Admin, Invoice Reviewer, or Approver; check seat availability before sending.
- Approver assignment: optional; can be completed later.
- Referral code: optional, only if already supported or a launch purpose is approved.
- Company registration number and tax ID: not collected in onboarding.
- Optional fields may be empty; the API records completion rather than forcing every answer.

### 4. Frontend session and cache behavior

- React Query keys must include the active organization ID and resource parameters. The current AP hooks already include the workspace ID; keep that convention.
- Default `staleTime`: 30 seconds. Reference data (chart of accounts, vendors, tax mappings) may use 5 minutes. Live queues may use 15–30 seconds. Approval and sync status may poll only while non-terminal.
- Invalidate the affected keys after every mutation, plus aggregate/queue keys. Do not require a manual refresh.
- Clear cached business data on logout and on organization switch. The current AP hook comment says data “stays warm” across workspace switches; that conflicts with the roadmap. Replace it with explicit removal of organization-scoped queries.
- Do not persist React Query state. Do not store tokens, OTPs, permissions, or raw documents in `localStorage` or `sessionStorage`.
- Persist only non-sensitive UI preferences such as the active workspace ID and theme.
- BFF route handlers and authenticated API responses use `cache: "no-store"`.
- Backend Redis keys stay organization-scoped with short TTLs and explicit invalidation. Never cache OTPs, sessions, tokens, raw documents, or authorization decisions beyond a short, explicitly invalidated TTL.
- Add `Cache-Control: no-store` to auth, permission, document, export, and status-report responses.
- Cache tests must cover logout, organization switch, role change, membership removal, and post-mutation staleness.

### 5. Intake: upload and forwarding email

**Upload**

- Reuse the existing upload route and upload service.
- Validate MIME type by content signature, file size, and allowed extensions.
- Store the original in private storage with an immutable content hash.
- Create one document record per accepted file.
- Batch upload returns per-file success/failure and a batch correlation ID.
- Duplicate file hashes remain a reviewable condition, not a silent delete.
- Allow an authorized user to upload an intentionally repeated document with an explicit override, recorded in audit.

**Email intake**

- One forwarding address per organization, created by an administrator and rotatable.
- The inbound provider calls a signed webhook. Verify signature, timestamp, event ID, recipient address, and replay window.
- Persist the inbound event before processing attachments. Use a unique idempotency key built from address, provider message ID, attachment index, and content hash.
- Ingest SPF, DKIM, and DMARC results. A failure quarantines the message and its attachments for human review. Do not silently accept or reject.
- Scan attachments before OCR. A failed scan moves the document to quarantine and notifies the workspace administrator.
- Enforce attachment count, byte size, total message size, sender rate, and organization rate limits.
- Email attachments and uploads must produce the same document type, status, duplicate fingerprint, storage policy, and processing timeline.
- The existing HMAC webhook and attachment idempotency table are the seam. Extend them; do not add a second inbound pipeline.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/v2/documents` | Single upload |
| POST | `/api/v2/documents/batch` | Batch upload |
| GET | `/api/v2/documents` | Organization-scoped list with filters |
| GET | `/api/v2/documents/{id}` | Document detail |
| GET | `/api/v2/documents/{id}/workflow` | Processing timeline |
| POST | `/api/v2/documents/{id}/retry-processing` | Retry failed processing |
| GET | `/api/v2/ap/email-address` | Show the forwarding address |
| POST | `/api/v2/ap/email-address` | Create or rotate it |
| POST | `/api/v2/ap/email/inbound` | Provider webhook; signature-verified and idempotent |

**UI states**

- Upload: idle, drag-active, selected, uploading, per-file success, per-file error, duplicate prompt, quota warning, quota paused.
- Email: address loading, copied, rotation confirmation, inbound-quarantine explanation.
- Document: queued, reading, extracting, needs review, ready, failed, quarantined, duplicate review, archived.

### 6. Extraction, validation, duplicates, and anomalies

**Pipeline**

1. OCR worker reads private storage and writes immutable OCR text/metadata.
2. Extraction engine returns typed header and line-item candidates with confidence and raw evidence.
3. Deterministic validation checks arithmetic, dates, currency, supported document type, supplier match, duplicate fingerprints, and PO/receipt consistency.
4. Clean documents may receive coding suggestions. Any uncertain or mismatched value becomes an exception or review item.
5. A human confirms corrections. Original OCR/extraction remains immutable; corrections store actor, prior value, new value, source, and timestamp.

**Validation rules**

- `subtotal + tax - discount = total` within a one-cent rounding tolerance per currency.
- Line totals sum to subtotal within the configured tolerance.
- Tax rate and tax amount are internally consistent when both are present.
- Invoice date is a real date and not implausibly future-dated.
- Due date is not before invoice date unless explicitly waived.
- Currency is a supported ISO code. A currency different from the workspace currency is flagged for FX review.
- The invoice amount and currency are preserved exactly as extracted and confirmed; validation never rewrites them into the workspace currency.
- Supplier name/number matches an existing vendor or is flagged unknown.
- Content hash, normalized invoice number, supplier, amount, currency, and date are checked for duplicates across upload and email.
- A suspected duplicate becomes `duplicate review`; it is never silently rejected or deleted.

**Data**

- Reuse `documents`, `document_analyses`, `document_line_items`, OCR/extraction records, `invoice_exceptions`, and the verification/duplicate services.
- Add only missing evidence fields: model/provider/version, prompt version, input hash, confidence per field, raw value, selected value, correction actor/time.
- Store money as fixed-precision decimals plus ISO currency. Never use floating point for validation or totals.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| PATCH | `/api/v2/documents/{id}/capture` | Save corrected header/lines |
| POST | `/api/v2/documents/{id}/analyze` | Re-run analysis |
| POST | `/api/v2/documents/{id}/review` | Mark human review outcome |
| GET | `/api/v2/ap/exceptions` | Exception queue |
| GET | `/api/v2/ap/exceptions/{document_id}` | Document exceptions |
| POST | `/api/v2/ap/exceptions/{id}/resolve` | Resolve with evidence |
| POST | `/api/v2/ap/exceptions/{id}/waive` | Waive with reason and authority |

**UI states**

- Field confidence: high/medium/low with text, not color alone.
- Validation summary: pass, warning, blocking.
- Duplicate: candidate list, match reasons, keep/reject/merge decision.
- Vendor: matched, ambiguous, unknown, create/link action.
- Processing: progress, current step, safe error code, retry.
- Currency: original currency badge, workspace-currency comparison labelled “for limit comparison only,” and provider posting status.

### 7. Vendors, chart of accounts, and provider reference data

- Reuse the vendor service, vendor sync, external-ID storage, and vendor controls.
- Add a provider-neutral import contract with `provider` as an explicit parameter. The service dispatches to the connected provider adapter; it never guesses from the connection table's first row.
- Supplier import maps external contacts to local vendors by external ID first, then normalized name/email.
- Chart-of-accounts import maps accounts by external ID/code. Keep only active, postable expense/asset/liability accounts eligible for coding.
- Purchase-order import is provider-dependent:
  - Xero: supported; Xero remains the source of truth for its POs.
  - QuickBooks Online: supported if the existing PO sync class is verified; do not claim it before verification.
  - Sage Accounting: purchase-order sync is not in the agreed AP scope; use manual or CSV POs and disclose the limitation. Do not use Products & Services or another excluded resource to fill the gap.
- When no provider is connected, allow manual vendor creation and a starter COA seed. Manual AP must not depend on an import.
- If an invoice vendor is not linked, require a human link or creation before bill sync. Do not auto-create a provider contact silently during sync.
- Create a provider contact only through an explicit, audited “create supplier in accounting system” action.
- Import is idempotent. Re-running it updates external fields and never duplicates records.
- Show counts, last sync time, and per-resource errors in the UI.
- Keep the existing QuickBooks code. It is active MVP code now, not deferred code.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/vendors` | Search/list vendors |
| POST | `/api/v2/vendors` | Create a vendor manually |
| PATCH | `/api/v2/vendors/{id}` | Edit vendor |
| POST | `/api/v2/integrations/{provider}/sync/vendors` | Import/link suppliers for `xero`, `quickbooks`, or `sage` |
| GET | `/api/v2/ap/chart-of-accounts` | List accounts |
| POST | `/api/v2/ap/chart-of-accounts/sync` | Sync from the active accounting provider |
| POST | `/api/v2/ap/chart-of-accounts/seed` | Seed starter accounts when no provider is connected |
| GET | `/api/v2/integrations/{provider}/capabilities` | Return supported sync resources, including PO support |

### 8. Purchase orders, receipts, and matching

**Scope decision**

The roadmap governs matching: an invoice may reference zero, one, or many POs and receipts. The user request mentions “one-invoice-to-one-PO” matching. That narrower model is not the launch contract. This spec implements the roadmap model and records the contradiction separately.

**Provider PO behavior**

| Provider | PO import | PO source of truth | MVP behavior |
|---|---|---|---|
| Xero | Yes | Xero | Import POs; a PO change after allocation flags the match without rewriting it. |
| QuickBooks Online | Verify existing sync coverage | QuickBooks Online | Import if verified; otherwise manual/CSV with a clear limitation. |
| Sage Accounting | Not in the agreed AP scope | InvoiAI manual/CSV record | Do not show a PO sync action; explain the limitation and use manual/CSV POs. |
| No connection | No | InvoiAI manual/CSV record | Manual/CSV POs and receipts remain available. |

**Data**

- Keep existing `purchase_orders`, PO lines, `goods_receipts`, `goods_receipt_lines`, `documents.purchase_order_id` for compatibility, and `matching_tolerances`.
- Add one allocation table for line-level partial matching:
  - organization ID
  - document ID
  - invoice line item ID
  - purchase order ID
  - PO line ID
  - goods receipt ID (nullable)
  - receipt line ID (nullable)
  - allocated quantity
  - allocated amount
  - currency
  - status (`allocated`, `voided`)
  - void reason, actor, timestamps
- A unique constraint prevents double-allocating the same invoice line to the same PO/receipt line beyond its quantity.
- Receipt quantities are accumulated from confirmed, non-voided receipt lines. Allocations reference the receipt lines they consume.
- Voiding an allocated receipt requires a reason and audit event. It does not silently mutate the invoice.

**Matching algorithm**

1. Determine mode: non-PO, two-way, three-way, or auto.
2. In two-way mode, require a PO. Compare supplier, currency, totals, line quantity, unit price, and tax within tolerances.
3. In three-way mode, require a confirmed receipt. Compare invoice quantity against accumulated received quantity and PO price.
4. Allocate invoice quantities to PO/receipt lines. Support partial invoices and partial deliveries.
5. Persist allocations. If an allocation cannot be completed, create a blocking exception.
6. A successful match sets `matched` or `partial_match`; it never sets `approved`.
7. A PO change after allocation flags the match for review. Do not rewrite the allocation silently.

**Tolerances**

- Price: default 2% or a configurable absolute cap.
- Quantity: default 0% for three-way unless a partial receipt exists.
- Tax total: exact match by default.
- Tolerances are per organization and may be overridden per transaction by an authorized administrator.
- Every tolerance change and waiver is audited.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/purchase-orders` | List/search POs |
| POST | `/api/v2/purchase-orders` | Manual PO |
| PATCH | `/api/v2/purchase-orders/{id}` | Edit PO; triggers match review if allocated |
| POST | `/api/v2/integrations/{provider}/sync/purchase-orders` | Import POs where supported |
| GET | `/api/v2/goods-receipts/po/{po_id}` | Receipts for a PO |
| POST | `/api/v2/goods-receipts` | Record receipt |
| POST | `/api/v2/goods-receipts/import` | CSV receipt import |
| POST | `/api/v2/goods-receipts/{id}/void` | Void with reason |
| GET | `/api/v2/ap/matching/purchase-orders` | Candidate POs for a vendor |
| GET | `/api/v2/ap/matching/receipts/{po_id}` | Receipts for matching |
| POST | `/api/v2/ap/documents/{id}/run` | Run matching/coding workflow |
| GET | `/api/v2/ap/documents/{id}/status` | Match and workflow status |

**UI states**

- No PO required / PO required / no candidate PO.
- Provider PO sync available / not available for this provider / manual PO required.
- Match passed / partial match / exception / waived.
- Per-line allocation view with remaining quantity and amount.
- Receipt accumulation timeline.
- Clear block on approval when unmatched or out of tolerance.

### 9. GL coding

- Reuse the rule-based coding service, AI suggestion path, coding rules, and line-level coding records.
- Coding runs after extraction and vendor resolution, before approval.
- Rule precedence: exact vendor rule, description/SKU pattern, historical vendor/account, then AI suggestion.
- Every suggestion includes source (`rule`, `historical`, `ai_suggested`, `manual`) and a short explanation.
- A human approves coding. Approved coding is required before bill creation.
- A line with no active postable account is a blocking exception.
- A coding change after approval is a critical-field change and revokes approval.
- Do not let AI choose tax treatment or post entries. Tax data is extracted and mapped, not determined.
- Coding works with a seeded/manual COA when no provider is connected.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/ap/codings/{document_id}` | Line coding |
| PUT | `/api/v2/ap/codings/{document_id}/line/{line_item_id}` | Save line coding |
| POST | `/api/v2/ap/codings/{document_id}/approve` | Approve coding |
| GET/POST | `/api/v2/ap/coding-rules` | List/create rules |
| PATCH | `/api/v2/ap/coding-rules/{id}` | Update rule |

### 10. Approval and separation of duties

- Reuse `ApprovalEngine`, `APRoutingEngine`, authority service, SoD service, delegations, approval history, and the existing queue routes.
- Approval is required before bill creation and before payment export.
- Limits are stored and compared in the workspace currency.
- A foreign-currency invoice is converted at the invoice-date rate for limit comparison only. The original amount/currency is preserved. The invoice is flagged for FX review.
- The submitter cannot approve their own invoice above the configured self-approval threshold (default £500 in GBP workspaces; use the workspace-currency equivalent in other markets).
- An owner/admin may self-approve below the threshold with an audit event.
- A match exception or coding exception blocks approval unless an authorized approver waives it with a reason. Waivers are audited.
- Critical fields: supplier identity, invoice number, invoice date, currency, total, tax, line amounts, GL coding, PO/receipt allocation.
- On a critical-field change after approval:
  - Mark the prior approval invalid/revoked.
  - Recompute the approval plan.
  - Return the document to `awaiting_approval`.
  - Record the changed field, prior/new value, actor, and reason.
- A successful match never auto-approves.
- Overdue steps escalate using the existing worker. Delegations expire automatically.
- Only administrators may change limits, delegations, and SoD rules.
- The last owner cannot be removed or demoted.
- Approval does not depend on an accounting connection.

**Routes**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/approvals` | Pending approval queue |
| GET | `/api/v2/approvals/overdue` | Overdue queue |
| GET | `/api/v2/approvals/document/{document_id}/history` | Decision history |
| POST | `/api/v2/approvals/{step_id}/decide` | Approve/reject with comment |
| GET/POST/PATCH/DELETE | `/api/v2/ap/rules` | Approval rules |
| GET/POST/DELETE | `/api/v2/ap/groups` | Approval groups |
| GET/PUT | `/api/v2/organization-access/authorities` | Limits and authorities |
| GET/POST | `/api/v2/organization-access/delegations` | Delegations |
| POST | `/api/v2/organization-access/delegations/{id}/revoke` | Revoke |

### 11. Accounting connections and provider write-back

#### 11.1 Common connection lifecycle

- The provider set is `xero`, `quickbooks`, and `sage`. `IntegrationProvider` already contains all three values; the service layer does not.
- At launch, a workspace has **at most one active accounting connection across all providers**. Connecting a second provider requires an explicit switch flow, not two silent active rows.
- Enforce the rule in the service and, where the existing data allows, with a partial unique index on `(org_id)` for active connections. If staging contains conflicting rows, reconcile them before applying the migration.
- Keep OAuth state validation, encrypted token storage, refresh, and revoke. Never return provider tokens to the client or write them to logs.
- The OAuth callback must **not** auto-select an organization. It stores the token set, marks the connection `organization_selection_required`, and returns the authorized organizations.
- The administrator confirms exactly one organization. Persist its external ID, display name, and region where applicable.
- Connection status values: `disconnected`, `authorizing`, `organization_selection_required`, `connected`, `reconnect_required`, `error`, `disabled`.
- Require MFA step-up for connect, reconnect, organization switch, provider switch, and disconnect.
- Reconnect replaces tokens on the same connection row; it must not create a duplicate connection.
- Switching organization or provider after bills exist requires:
  - administrator confirmation,
  - MFA step-up,
  - a sync check that no in-flight or approved-but-unsynced bills target the old organization,
  - an audit event.
- A connection can be disconnected at any time. Disconnecting does not delete local documents, approvals, payment instructions, or audit history. It also does not void provider bills.
- Show the connected organization name, provider, status, last successful sync, last error, and supported resources on the integrations page.
- The manual AP workflow remains available when the connection is missing, expired, errored, or unsupported.

#### 11.2 Xero

**Connection and organization selection**

- Keep the existing OAuth authorization URL, state validation, token encryption, refresh, and revoke.
- Change the callback so it does **not** call `get_tenant()` or auto-select `connections[0]`.
- Fetch all authorized Xero connections, store the token set, and return `tenantId`, `tenantName`, and connection status.
- Persist the selected `tenant_id` and display name only after the administrator confirms.
- One Xero tenant per workspace at launch.
- Use the stored tenant ID for the `xero-tenant-id` header on every request. Do not derive it from the first connection.

**Client and imports**

- The current `XeroClient` is GET-only. Add POST/PUT support and expose the endpoints needed for contacts, accounts, purchase orders, and invoices.
- Supplier import maps Xero contacts to local vendors by external ID, then normalized name/email.
- COA import maps Xero accounts to local accounts by external ID/code. Keep only postable expense/asset/liability accounts eligible for coding.
- PO import maps Xero purchase orders and lines. Xero remains the source of truth for its POs.
- Import is idempotent. Re-running it updates external fields and never duplicates records.
- Show counts, last sync time, and per-resource errors in the UI.
- A PO change in Xero after allocation flags the local match for review; it does not silently rewrite the allocation.

**Approved-bill write-back**

- Implement `XeroAccountingProvider` behind the existing provider abstraction.
- Support `create_bill`, `update_bill`, `get_bill`, `find_bill`, `sync_chart_of_accounts`, `sync_vendor`, `sync_purchase_orders`, and `supports_purchase_orders`.
- Payload:
  - `Type: ACCPAY`
  - contact reference (Xero contact ID)
  - invoice number
  - invoice date and due date
  - original currency code
  - original line amounts, descriptions, tax type, account code
  - a safe reference to the InvoiAI document ID
- Use the existing `BillSyncWorker` claim: `APPROVED → SYNCING_TO_ERP`, provider call, local verification, rollback to `APPROVED` on failure.
- Before creating:
  - verify the document is approved and AP-enabled,
  - verify no existing `erp_bill_id`,
  - verify approved line coding with active accounts,
  - verify a linked supplier,
  - verify the currency policy for the tenant.
- Idempotency:
  - Add a stable `erp_sync_key` derived from organization, document, supplier, invoice number, total, currency, and invoice date. Enforce a unique constraint.
  - Before POST, query Xero for an existing `ACCPAY` bill matching the contact and invoice number. If exactly one matches and amounts/dates/currency agree, adopt its ID instead of creating another.
  - If the query returns an ambiguous result, fail visibly and require reconciliation; never guess.
  - If a POST times out, reconcile by query on retry before posting again.
  - Do not assume a Xero idempotency header. Use local uniqueness plus reconciliation unless official documentation for the exact endpoint confirms a key.
- Persist `erp_bill_id`, `erp_synced_at`, attempts, last error, and last attempt time.
- On success, transition to the payment-ready state through the existing state machine and evaluate payment authorization.
- On failure, keep the invoice visible in `Sync failed` with a safe error code and a retry action. Do not lose the approval or the local record.
- Retry with bounded exponential backoff. Classify:
  - auth/token failure → prompt reconnect,
  - 429 → backoff with `Retry-After`,
  - 5xx/timeout → retry,
  - validation/4xx → stop and show the exact field problem,
  - duplicate ambiguity → manual reconciliation.
- The local void/archive action does not imply the Xero bill was voided. Show the distinction and require a separate accounting action.

#### 11.3 QuickBooks Online

**Connection and organization selection**

- Keep the existing QuickBooks OAuth, realm storage, client, sync classes, and `QuickBooksAccountingProvider`.
- Show the company name for the connected realm. The realm ID is not a user-friendly organization name.
- If the administrator authorizes a different company, require a separate explicit connection/switch; do not silently replace the realm.
- One QuickBooks realm per workspace at launch.

**Imports**

- Reuse the existing vendor and chart-of-accounts sync classes.
- Confirm whether the existing purchase-order sync class covers the launch PO fields. If it does not, either complete it or mark QuickBooks PO import as unavailable and use manual/CSV POs.
- Import is idempotent and maps by external ID first.
- Do not auto-create a QuickBooks vendor during bill sync. Use an explicit audited action.

**Approved-bill write-back**

- Reuse `QuickBooksClient.create_bill` and `update_bill` and the existing provider adapter.
- Remove the hardcoded USD default in `BillSyncService`. Use the document currency and the provider's currency rules.
- Payload must include the vendor reference, document number, dates, currency, line amounts, account references, and a safe memo/reference to the InvoiAI document.
- Duplicate protection audit:
  - Confirm what happens when a POST times out after QuickBooks created the bill.
  - Confirm what happens when two workers claim the same document.
  - Add the same `erp_sync_key` unique constraint and pre-flight `find_bill` reconciliation used for Xero.
  - Adopt an exact existing bill; fail on ambiguity.
- Keep the existing `erp_bill_id` link and add provider sync state.
- Classify errors the same way as Xero: reconnect, rate limit, retry, stop, reconcile.
- A local void/archive does not imply the QuickBooks bill was voided.

#### 11.4 Sage Accounting — required MVP provider

Sage is a required MVP provider, not an optional or deferred connector. The adapter is limited to the resource areas in 5.5: User Accounts, Contacts, Chart of Accounts, Purchase Transactions, Status Codes & Types, Currencies, Taxes, and relevant Settings. Attachments are optional and not in the first slice. The exact product/edition/version, region, authorization, endpoints, and field shapes must be recorded before implementation.

**Connection and business selection**

- OAuth 2.0 authorization code. Read the authorize URL, token URL, scopes, redirect rules, and regional base URL from official documentation and the registered app; do not copy endpoints from another Sage product or from an unverified comment.
- Store tokens with the existing encrypted token service; never return them to the client.
- The callback must not select a business automatically. Store the token set and return the businesses available through User Accounts.
- The administrator selects exactly one business. Persist external business ID, display name, and region.
- Send whatever business-selection header or parameter the verified API requires on every scoped request. Do not assume a header name.
- Connection states reuse the common lifecycle: `disconnected`, `authorizing`, `business_selection_required`, `connected`, `reconnect_required`, `error`, `disabled`.

**Reads**

- **User Accounts:** identify accessible businesses only.
- **Contacts:** supplier matching. Map by external contact ID first, then normalized supplier name. Do not import personal or bank details the AP workflow does not need.
- **Chart of Accounts:** active postable accounts only; map by external ID/code; record last sync and per-account errors.
- **Status Codes & Types:** read-only; map provider transaction type/status to local sync state.
- **Currencies:** read-only; return supported, rate required, or unsupported with a safe reason.
- **Taxes:** read-only; map existing provider tax references to invoice lines. Never determine tax or file returns.
- **Settings:** read only the business/accounting configuration needed by the integration.
- **Attachments:** do not implement in the first slice. Revisit only with a verified capability and a customer workflow that needs the file in Sage.

**Writes: Purchase Transactions**

- Create one approved supplier invoice after local approval and authorization checks. Update only where the verified API supports it.
- Create/update relevant supplier credit notes only if the verified app permission and API support it; otherwise keep credit records local and clearly labelled.
- Use the verified field contract. At minimum the payload must carry supplier contact reference, invoice number/reference, invoice date, due date, original currency, line descriptions, quantities, unit prices, account references, and existing tax references.
- Read the created/updated transaction back and compare supplier, reference, amount, currency, date, and line count before marking it synced.
- Never post before approval, never post twice, and never post to a business the administrator did not select.

**Currency**

- Read Currencies before every write.
- Supported → post in the invoice currency.
- Rate required → require a human-confirmed rate, store rate/source/actor, then allow retry. Do not look up or infer a rate.
- Unsupported → set `blocked_currency`, keep the invoice approved, keep manual payment export available, and show a safe reason.
- Never change the stored invoice amount or currency.

**Idempotency, retry, and duplicate prevention**

- No provider idempotency key is assumed.
- Use `erp_sync_key` as the local uniqueness guard.
- Before creating, query Purchase Transactions by supplier contact and invoice reference, then compare amount, date, currency, and line shape.
- Exactly one matching transaction → adopt its ID.
- Zero → create.
- More than one, or a mismatched match → stop with `ACCOUNTING_DUPLICATE_AMBIGUOUS`; never create another.
- A timeout after create is not proof of failure. Reconcile before retry.
- Classify errors: 401/403 reconnect; 429 backoff with `Retry-After`; 5xx/timeout retry; 4xx validation stop and show the field-level reason.
- Record provider, operation, correlation ID if available, external ID, HTTP status, safe error code, and timestamp for every attempt.

**Boundary enforcement**

- The adapter must not call Sage Banking, Payments & Receipts, bank-account resources, general journal/ledger resources, Sales Transactions, Opening Balances, Products & Services, or Reporting.
- Add a negative contract test that fails if the adapter calls an excluded resource.
- No tax determination, tax filing, payment initiation, or bank connection is performed through Sage.
- If a required field is unavailable in the agreed resource areas, record the limitation and keep manual AP available; do not substitute an excluded resource.

**Verification and rollout**

- Build behind a feature flag and do not expose a working-looking Sage card until trial-business evidence exists.
- Sage trial-business evidence must cover: API 3.1, business selection, supplier read, COA read, status/type read, currency read for GBP/USD/NGN, tax read, one approved purchase invoice create, timeout reconciliation, retry without a duplicate, and a negative check for excluded resources.
- Record evidence in the ADR and Sage trial-business evidence log. A mocked adapter call is not launch evidence.

#### 11.5 Provider-neutral write-back contract

**Interface**

Extend the existing `AccountingProvider` ABC so every adapter has the same shape:

| Method | Contract |
|---|---|
| `provider_name` | `xero`, `quickbooks`, or `sage` |
| `list_organizations()` | Return authorized organizations with external ID, display name, and status |
| `select_organization(external_id)` | Persist the chosen organization after confirmation |
| `supports_purchase_orders()` | Return whether the provider can import POs |
| `sync_vendor(...)` | Import/update suppliers idempotently |
| `sync_chart_of_accounts(...)` | Import/update the COA idempotently |
| `sync_purchase_orders(...)` | Import POs where supported; otherwise raise a typed unsupported error |
| `validate_currency(...)` | Return `supported`, `requires_rate`, or `unsupported` with a reason |
| `create_bill(...)` | Create an approved bill and return the external ID |
| `update_bill(...)` | Update an existing external bill |
| `get_bill(...)` | Read one bill by external ID |
| `find_bill(...)` | Reconcile by supplier, invoice number, amount, date, and currency |
| `void_bill(...)` | Optional; only where the provider supports an explicit void/cancel |

`get_accounting_provider(provider)` returns the configured adapter for all three providers. It must not raise `NotImplementedError` for a provider that is in MVP scope; it raises a typed `ProviderNotConfiguredError` only when credentials or selection are missing. The Sage adapter implements `sync_purchase_orders` as a typed unsupported operation and has no attachment capability in the first slice.

**Worker flow**

1. `BillSyncWorker` loads the document and its active accounting connection.
2. It verifies `ap_enabled`, `ap_status == approved`, no existing `erp_bill_id`, approved coding, linked supplier, and currency policy.
3. It claims `APPROVED → SYNCING_TO_ERP` with a compare-and-set update.
4. It calls `provider.find_bill(...)` before creating.
5. If exactly one match exists, it adopts the external ID.
6. If no match exists, it calls `provider.create_bill(...)`.
7. It verifies the returned bill by reading it back and comparing supplier, number, amount, currency, and date.
8. It persists `erp_bill_id`, `erp_provider`, `erp_synced_at`, and clears the transient error.
9. It transitions to the payment-ready state and evaluates payment authorization.
10. On failure, it rolls back to `APPROVED`, records a safe error code and attempt, and leaves a visible retry action.

The worker must be safe to run twice. Concurrent claims must produce one provider POST.

**Idempotency and duplicate protection**

- `erp_sync_key` is the local uniqueness guard. It is derived deterministically and stored per organization.
- A unique constraint prevents two documents with the same key from syncing independently.
- The pre-flight reconciliation query is mandatory for all three providers.
- Exactly one match → adopt.
- Zero matches → create.
- More than one match, or a match whose amount/date/currency disagrees → stop with `ACCOUNTING_DUPLICATE_AMBIGUOUS`; never create another.
- A timeout after POST is not proof of failure. Reconcile before retrying.
- Record every attempt: provider, operation, request correlation ID if available, external ID if returned, safe error code, HTTP status, and timestamp.

**Currency gate**

- The provider adapter returns a currency decision before any POST.
- `unsupported` → set `erp_sync_status = blocked_currency`, `erp_currency_status = unsupported`, and keep the document approved and exportable.
- `requires_rate` → require a human-confirmed rate, store the rate, source, and actor, and only then allow a retry.
- `supported` → proceed.
- The invoice's stored amount/currency never changes.

**Void and archive**

- A local void/archive is not a provider void.
- If the provider supports void/cancel, expose it as a separate, explicit action with its own permission, confirmation, audit event, and failure state.
- If the provider does not support void, say so; do not imply the ledger was reversed.
- Deleting a local document never deletes a provider bill.

**Manual path**

- If no provider is connected, the worker is not involved.
- The document can still be approved, exported for payment, and tracked with customer-reported status.
- The UI must show “No accounting connection — manual AP” and offer “Connect accounting” without blocking the workflow.

#### 11.6 Currency policy

- Workspace currency defaults: UK → GBP, US → USD, Nigeria → NGN suggested, others → user-selected ISO.
- Invoice currency is immutable after approval unless a critical-field reapproval occurs.
- The provider adapter decides whether the invoice currency can be posted. The decision is based on the connected organization's configuration, not on a global assumption.
- No automatic FX rate lookup in the MVP. If a provider requires an exchange rate, a human enters or confirms it; record the source and actor.
- A displayed conversion for approval limits is explicitly labelled “for limit comparison only” and is not reused as the posting rate.
- If the provider cannot post the currency:
  - keep the invoice approved,
  - set a visible currency-status reason,
  - keep manual payment-instruction export available,
  - do not claim the bill exists in the provider.
- NGN invoices are preserved and can move through manual AP. Posting NGN is provider- and account-dependent; do not claim NGN localization or universal NGN posting.
- Subscription billing currency is separate. Do not use invoice currency behavior to justify Stripe pricing.

#### 11.7 Routes

Use a provider path parameter so the frontend and tests exercise one contract. Preserve the existing provider-specific QuickBooks and Xero paths as aliases where practical.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/integrations` | All provider statuses, connected organization, last sync, last error, capabilities |
| POST | `/api/v2/integrations/{provider}/connect` | Start OAuth for `xero`, `quickbooks`, or `sage` |
| GET | `/api/v2/integrations/{provider}/callback` | Exchange code; never select an organization |
| GET | `/api/v2/integrations/{provider}/organizations` | List authorized organizations/tenants/realm/businesses |
| POST | `/api/v2/integrations/{provider}/organization` | Confirm the selected organization |
| DELETE | `/api/v2/integrations/{connection_id}` | Disconnect; keep local records |
| POST | `/api/v2/integrations/{provider}/sync/vendors` | Import suppliers |
| POST | `/api/v2/integrations/{provider}/sync/chart-of-accounts` | Import COA |
| POST | `/api/v2/integrations/{provider}/sync/purchase-orders` | Import POs where supported |
| GET | `/api/v2/integrations/{provider}/capabilities` | Supported resources, including PO availability |
| POST | `/api/v2/ap/documents/{document_id}/create-bill` | Queue approved-bill creation |
| POST | `/api/v2/ap/documents/{document_id}/retry-bill-sync` | Explicit retry/reconcile |
| GET | `/api/v2/ap/documents/{document_id}/status` | Sync state, provider, bill ID, currency status, error |

Existing paths remain valid during migration:

- `/api/v2/integrations/quickbooks/*`
- `/api/v2/integrations/xero/*`

Sage routes are MVP routes. The handler may return a verification/capability state until trial-business evidence is recorded, but the route must not disappear or imply Sage is optional.

#### 11.8 UI states

- Disconnected: provider card with “Connect” and a manual-AP explanation.
- Authorizing: progress and cancel.
- Organization selection required: list of authorized organizations; no default selection.
- Connected: organization name, provider, status, last sync, last error, supported resources.
- Reconnect required: clear token-expired message and a reconnect action.
- Error: safe reason, retry, and support path.
- Switching organization or provider: confirmation, in-flight/unsynced bill check, MFA step-up, audit notice.
- Sync: not started, in progress, synced, failed (with reason), retry available.
- Capabilities: suppliers, COA, POs, and currency support shown per provider; Sage Accounting shows only the agreed AP resources, and PO sync is unavailable with a manual/CSV explanation.
- Currency: “Original currency preserved,” “Posting supported,” “Review required — automatic bill creation is disabled,” or “Provider rejected this currency.”
- Manual AP: “No accounting connection — approve and export without syncing.”
- Tax mapping: show only for providers that support it. For Sage, show a read-only mapping of verified existing tax references; never present it as tax determination or filing.

### 12. Payment instructions, exports, and customer-reported status

**Boundary**

InvoiAI prepares instructions only. It does not collect bank credentials, initiate transfers, or execute supplier payments. Mock/provider execution remains disabled.

**Instruction model**

- Reuse `payment_instructions` and `payment_instruction_events`.
- Keep amount and currency as captured on the invoice.
- Keep the existing status machine for internal instruction lifecycle, but expose a separate payment-handoff view:
  - approved and ready for export,
  - exported,
  - customer-reported paid,
  - customer-reported failed/returned.
- Do not overload one field to mean both “bill created” and “payment authorized.”
- Payment export is available whether or not the accounting sync succeeded.

**CSV export**

Columns: workspace, supplier, invoice number, invoice date, due date, amount, currency, payment reference, instruction ID, status, customer-reported status. No bank account or routing credentials. Use fixed decimal formatting and RFC 4180 quoting.

**PDF export**

A printable instruction sheet with the same fields plus a totals summary and a “customer-reported, not bank-verified” label. Add one PDF-generation dependency only for this feature (for example, a small pure-Python PDF writer). If the dependency is rejected, serve a print-optimized HTML page and require browser print-to-PDF, but label that behavior explicitly.

**Customer-reported status**

Add an append-only status-report record:

- organization ID
- document ID
- payment instruction ID (nullable)
- reported status (`paid`, `partially_paid`, `failed`, `returned`, `unknown`)
- paid date
- amount and currency
- bank/payment reference
- note
- reported by
- created at
- source = `customer_reported`
- idempotency key to prevent duplicate submissions

The latest report drives the UI label. History is never overwritten. A customer-reported paid status does not imply bank verification; only an actual reconciliation source may use “confirmed.”

**Routes**

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/ap/payments/queue` | Authorized/ready queue |
| POST | `/api/v2/ap/payments/{document_id}/evaluate` | Re-evaluate authorization |
| GET | `/api/v2/ap/payments/export?format=csv\|pdf` | Batch export with filters |
| POST | `/api/v2/ap/payments/{document_id}/instructions` | Create instruction |
| GET | `/api/v2/ap/payments/{document_id}/instructions` | Instruction history |
| GET | `/api/v2/ap/payments/instructions/{id}/events` | Event history |
| POST | `/api/v2/ap/payments/instructions/{id}/cancel` | Cancel |
| POST | `/api/v2/ap/payments/{document_id}/status-reports` | Record customer-reported status |
| GET | `/api/v2/ap/payments/{document_id}/status-reports` | Status history |

**UI states**

- Ready for payment, blocked, needs review, override required.
- Exporting, exported, download ready, export failed.
- Customer-reported status form with required date/reference and a persistent “customer-reported” label.
- History timeline with actor and timestamp.
- Manual-AP notice when no accounting connection exists.

### 13. Dashboard, search, quota, and surface cleanup

- Keep the AP dashboard as an operational queue, not an analytics product.
- Search and filters are organization-scoped and URL-persisted. Use Postgres indexes; do not add a search engine.
- Show one primary next action per record: Review invoice, Resolve exception, Approve bill, Sync to accounting, Review currency, Export payment instructions, or Report payment.
- Show a manual-AP next action when no provider is connected.
- Disable personal finance: remove from navigation, redirect personal routes, and do not expose its APIs in the business workspace.
- Disable the vendor portal and bank-change collection for the AP MVP. Keep the code, gate it off.
- Remove the Free price ID and Free plan card. Replace them with the approved trial configuration; do not create a permanent free plan.
- Quota behavior: warn at 80% and 100%. At the limit, pause only new AI/OCR extraction. Manual creation/editing, approvals, accounting sync, export, and existing records continue. No overage charge and no lockout.
- Show the invoice allowance and seat usage as separate meters. Never merge invoice count and member count into one number.
- Seat enforcement: block a new invitation at the limit with a clear “add seats or remove access” message; changing a role or holding several roles changes nothing.
- Trial behavior: show the end date and invoice cap; at the end, keep read-only access plus export until a plan is chosen.
- Add audit events for document changes, coding overrides, approval decisions, payment exports, status reports, integration changes, organization/provider switches, role changes, seat changes, plan/trial changes, and quota pauses.

### 14. Data model and migrations

Use existing tables wherever possible. Add only the following contracts.

| Migration | Change | Reason |
|---|---|---|
| `20261107_identity_onboarding` | Organization onboarding fields; onboarding draft; membership business role; OTP challenge table; MFA recovery-code table; profile first/last name and optional mobile | Close auth/onboarding gaps |
| `20261108_pricing_seats_trial` | Plan catalog fields (`price_gbp`, `price_usd`, `invoice_allowance`, `included_seats`, `additional_seat_rate`); subscription trial fields; seat usage view/table derived from active memberships; allowance counters | Separate seats from invoice allowance, support trial and GBP/USD plans |
| `20261107_intake_hardening` | Inbound email auth results, quarantine state, attachment scan state, cross-channel duplicate index | Make email intake safe and idempotent |
| `20261107_ap_allocations` | Line-level allocation table and constraints; receipt void metadata | Support multi-PO/partial matching |
| `20261107_accounting_provider_neutral` | Provider-neutral connection fields: `provider`, `external_organization_id`, `external_organization_name`, `external_region`, `connection_status`, `last_sync_at`, `last_error_code`, `last_error_message`, `metadata`; backfill QuickBooks `realm_id` and Xero `tenant_id`; active-connection uniqueness | One connection contract for Xero, QuickBooks, and Sage |
| `20261107_erp_writeback` | `erp_provider`, `erp_sync_key` unique constraint, `erp_sync_status`, `erp_sync_attempts`, `erp_last_error_code`, `erp_last_error_message`, `erp_last_attempt_at`, `erp_currency_status`, `erp_currency_note`; reconcile existing `erp_bill_id` | Idempotent, observable provider write-back |
| `20261107_payment_reports` | Append-only customer-reported status table; export audit fields | Separate reported status from verified settlement |
| `20261107_rls_and_indexes` | RLS policies on tenant-owned tables; search/audit indexes | Launch security and performance gates |

Sage uses the provider-neutral connection and write-back fields above. Add a Sage-specific migration only if the verified trial-business evidence requires a field the neutral contract cannot hold, such as a business/region identifier or an optional attachment reference. Do not add tables or columns for excluded Sage resources.

**RLS tables**

At minimum: organizations, org_members, documents, document_line_items, document_analyses, vendors, purchase_orders, purchase_order_lines, goods_receipts, goods_receipt_lines, invoice_codings, invoice_exceptions, chart_of_accounts, approval_workflows, approval_steps, approval_history, payment_instructions, payment_instruction_events, payment_status_reports, integration_connections, audit_logs, usage, notifications.

Policies use active membership. Keep service-role access for workers. Do not rely on RLS alone; keep object-level service authorization.

**Constraints**

- Money columns are fixed-precision decimals with ISO currency.
- `documents` keeps separate ingest/OCR/approval/ERP-sync/payment-report states.
- Unique `erp_sync_key` per organization.
- Unique active accounting connection per organization at launch.
- Unique provider organization binding per active connection.
- Unique payment status idempotency key per organization.
- Unique allocation key per invoice line + PO line + receipt line.
- Unique active membership per organization + user, so one member cannot consume two seats.
- Seat count is derived from active memberships, never stored as a mutable counter that can drift.
- Subscription stores `currency`, `price_id`, `included_seats`, `invoice_allowance`, and trial fields; the invoice allowance is never derived from seat count.
- Invitation and reset tokens are hashed, expiring, single-use.
- Never store plaintext OTPs, recovery codes, OAuth tokens, or bank credentials.

### 15. API route summary

**New or changed**

- Auth: signup with first name, surname, and optional mobile; verify OTP; resend OTP; Google authorize/callback; MFA enroll/verify/challenge/recovery/factors.
- Onboarding: state, draft save, and complete; organization profile edit; market-aware currency default; optional invitations and approver assignment with seat check.
- Billing: GBP/USD plan catalog, checkout with seat quantity, subscription with trial/allowance/seat fields, seat usage, trial state, additional seats. Public plan endpoint exposes the live catalog without a permanent free tier.
- Integrations: provider-neutral connect/callback/organizations/organization/disconnect; capability endpoint; supplier/COA/PO imports; Xero tenant selection; QuickBooks company display; Sage business selection and connector scoped to the agreed AP resource areas.
- Accounting write-back: provider-neutral create-bill, retry/reconcile, status, currency reason.
- Payment: batch CSV/PDF export; customer-reported status reports.
- Intake: quarantine and scanning status in document/email responses.

**Preserved**

All existing document, AP, approval, purchase, goods-receipt, vendor, workspace, organization, integration, billing, and export routes remain unless explicitly superseded. Preserve URLs through redirects when navigation changes. Keep the existing QuickBooks routes as aliases during the transition.

**Error contract**

Use the existing structured error response. Add stable, provider-neutral codes:

- `EMAIL_NOT_VERIFIED`
- `MFA_REQUIRED`
- `MFA_INVALID_CODE`
- `OTP_EXPIRED`
- `OTP_ATTEMPTS_EXCEEDED`
- `OTP_RESEND_COOLDOWN`
- `ONBOARDING_INCOMPLETE`
- `SEAT_LIMIT_REACHED`
- `SEAT_USAGE_UNAVAILABLE`
- `TRIAL_EXPIRED`
- `TRIAL_INVOICE_CAP_REACHED`
- `ALLOWANCE_EXHAUSTED`
- `BILLING_CURRENCY_UNAVAILABLE`
- `PLAN_NOT_AVAILABLE_IN_REGION`
- `SMS_NOT_SUPPORTED`
- `WORKSPACE_ACCESS_DENIED`
- `DUPLICATE_DOCUMENT`
- `DOCUMENT_QUARANTINED`
- `QUOTA_EXTRACTION_PAUSED`
- `APPROVAL_REQUIRED`
- `APPROVAL_REVOKED`
- `MATCH_EXCEPTION`
- `CODING_INCOMPLETE`
- `ACCOUNTING_NOT_CONNECTED`
- `ACCOUNTING_ORGANIZATION_NOT_SELECTED`
- `ACCOUNTING_TOKEN_EXPIRED`
- `ACCOUNTING_RATE_LIMITED`
- `ACCOUNTING_SYNC_FAILED`
- `ACCOUNTING_DUPLICATE_AMBIGUOUS`
- `ACCOUNTING_CURRENCY_UNSUPPORTED`
- `ACCOUNTING_CURRENCY_RATE_REQUIRED`
- `ACCOUNTING_PO_NOT_SUPPORTED`
- `ACCOUNTING_PROVIDER_NOT_CONFIGURED`
- `ACCOUNTING_PROVIDER_SWITCH_BLOCKED`
- `SAGE_CAPABILITY_UNVERIFIED`
- `SAGE_RESOURCE_UNAVAILABLE`
- `FX_REVIEW_REQUIRED`
- `PAYMENT_REPORT_CONFLICT`

Provider-specific details belong in the audit/log record, not in the client message. Do not expose provider payloads, tokens, SQL errors, or stack traces to the client.

During migration, keep the existing `XERO_*` error codes as aliases mapped to the new provider-neutral codes so current clients do not break. New clients should use the provider-neutral codes and read provider-specific detail from the document/status response, not from the error string.

### 16. Worker behavior

- `OCRWorker` and `AnalysisWorker` continue to process by immutable document ID.
- `APMatchingWorker` reads the persisted allocation and writes exceptions/status.
- `APCodingWorker` uses the active provider's COA and writes line coding.
- `ApprovalWorker` handles escalation and overdue steps.
- `BillSyncWorker` remains the single bill-sync entry point and claims `APPROVED → SYNCING_TO_ERP` atomically.
- `BillSyncWorker` resolves the adapter from the active connection's provider; it does not hardcode QuickBooks.
- `XeroWorker` remains the inbound sync orchestrator; add explicit import commands for COA, vendors, and POs.
- `QuickBooksWorker` remains the inbound sync orchestrator; verify PO coverage and currency behavior.
- `SageWorker` is the Sage AP sync orchestrator. It must send the verified business-selection header and call only the agreed resource areas. It must never call Banking, Payments & Receipts, bank accounts, journals/ledger, Sales Transactions, Opening Balances, Products & Services, or Reporting.
- Every worker derives organization from the record. Never trust `org_id` or role from a job payload.
- Persist attempts, leases, safe error codes, and next-attempt time. Use bounded exponential backoff and a visible terminal failed state.
- Workers must be safe to run twice. External effects are idempotent or reconciled before retry.
- A worker failure must never delete the document, revoke approval, or block manual payment export.

## 6. Testing decisions

### What makes a good test

Test observable behavior at the highest seam that can exercise the risk. Assertions should describe what a user or operator can observe: HTTP status, response shape, persisted status, audit event, provider request count, and visible next action. Do not assert private method calls or implementation structure.

A provider feature is not “tested” by mocking the adapter and asserting it was called. At least one test per provider must exercise the real adapter against a fake HTTP transport that enforces the provider's request shape, and at least one recorded provider-environment smoke test per provider (Xero/QuickBooks sandbox or Sage trial business account) must be recorded before launch.

### Seams

**Primary seam: authenticated HTTP API.**

- Use the existing FastAPI app and `TestClient`/`httpx` client.
- Override `get_current_user` and `get_org_context` for role and tenant identity in the test, while keeping the real authorization dependency chain.
- Use a real Postgres/Supabase test database for document, approval, accounting-sync, and RLS tests. Do not mock the database for end-to-end workflow tests.
- Stub external HTTP at the client boundary (`httpx.MockTransport` or a fake provider), not inside services.
- This seam covers signup/OTP/onboarding, upload, review, matching, approval, provider write-back, export, and status reporting.

**Narrow seam: provider adapter contract, parameterized over Xero, QuickBooks Online, and Sage.**

- Use one provider-contract suite with a fake transport per provider.
- Assert: no POST before approval; exactly one POST on the first attempt; zero duplicate POSTs after a timeout when reconciliation finds the bill; retry after 5xx; stop on 4xx; correct organization header; correct currency decision; no PO call when the provider does not support POs.
- This is the only place where asserting call counts is appropriate, because duplicate-bill creation is the risk.

**Narrow seam: provider-specific transport.**

- Xero: `xero-tenant-id` header, `ACCPAY` payload, contacts/accounts/POs read shape.
- QuickBooks: realm scoping, Bill payload, vendor/COA read shape, currency field.
- Sage: verified business-selection header, verified token endpoint, Purchase Transactions payload, User Accounts/Contacts/COA/Currencies/Taxes read shapes, and a negative assertion that no excluded resource is called.

**Narrow seam: RLS and tenant isolation.**

- Use two authenticated Supabase clients against the test database to prove one tenant cannot select/update another tenant's rows.
- Repeat through API paths for list, detail, download, export, search, and worker execution.

**Frontend seam: one end-to-end path.**

- Add a browser E2E test for signup → OTP → resumable onboarding (including an optional invite) → upload → review → approve → provider test bill → export → status report.
- Add a second E2E path with **no accounting connection**: signup → onboarding with “no accounting software” → upload → approve → export → status report.
- Add a third E2E path for **trial and seats**: trial start without a card → invite at the seat limit → add seat → assign Approver role → trial end read-only/export.
- Add focused tests for Google button redirect, MFA challenge, workspace switch cache clearing, logout cache clearing, and unverified-user redirect.
- If a browser test runner is not already approved, add one runner only for these flows; do not add a second component-testing stack.

### Prior art in the repo

- `test_v2_auth_router.py` for auth request validation.
- `test_v2_verification_engine.py` for deterministic validation.
- `test_v2_quickbooks_worker.py` for provider worker shape and per-connection iteration.
- `test_payment_state_machine.py` and `test_payment_instruction_atomic_transition.py` for payment lifecycle.
- `test_ap_exception_repository.py` and `test_ap_chart_of_accounts_cache.py` for tenant-scoped AP behavior.
- `test_line_item_service.py` for decimal and line-item contracts.
- `conftest.py` for the app/client fixture; extend it for tenant/role overrides and test database setup.

### Required test matrix

| Area | Test |
|---|---|
| Signup | First name, surname, email, password accepted; optional mobile accepted without SMS; weak password rejected; duplicate email does not enumerate; no company/tax ID required |
| OTP | Correct email code verifies; expired code fails; five wrong attempts lock; resend cooldown; single use; NG signup completes with email only |
| Google | State/nonce validated; verified email links; unverified email creates separate account; cancel is handled |
| MFA | Owner/admin without factor is restricted; enrollment returns recovery codes once; AAL2 required for admin actions; recovery code single-use |
| Verification gate | Unverified user gets 403 on dashboard, documents, AP, approvals, integrations, exports |
| Onboarding | Draft saves and resumes; optional fields skippable; required fields validated; creator is owner; retry is idempotent; NG signup is not blocked; UK defaults to GBP; US defaults to USD; default is editable; “not yet registered” accepted; no company/tax ID field required |
| Seats | Unique active member counts once with multiple roles; pending invitation does not count; invite at limit blocked; role change does not change count; removal releases seat; downgrade below usage blocks new invites without removing members |
| Trial | Trial starts without a card; end date and cap visible; cap pauses new AI/OCR only; end without plan is read-only plus export; second trial on another workspace is blocked; no Free plan exists |
| Billing | GBP shown for UK and USD for US; checkout sends seat quantity not 1; allowance and seats independent; supplier-payment count never affects billing; plan cards come from the live catalog |
| Tenancy | Two users/two orgs cannot read, list, search, download, export, or process each other's records |
| Upload | Valid PDF/image accepted; spoofed type rejected; oversized rejected; duplicate prompts; batch partial success |
| Email | Invalid signature rejected; replay ignored; SPF/DKIM/DMARC failure quarantined; malware result quarantined; attachment idempotency |
| Extraction | Arithmetic mismatch flagged; bad date flagged; unknown vendor flagged; confidence/evidence preserved; original file immutable; NGN amount/currency preserved |
| Duplicate | Exact hash, normalized number/supplier/amount/date, and cross-channel duplicates flagged; nothing deleted |
| COA | Provider import idempotent for Xero, QuickBooks, and Sage; manual seed works; inactive accounts cannot be coded; cache invalidated |
| PO/receipt | Partial receipt accumulates; multi-PO allocation persists; over-allocation blocked; void requires reason; Sage shows no PO sync; manual PO works |
| Matching | Two-way pass/fail; three-way pass/fail; tolerance boundaries; match never approves; waiver requires reason/authority |
| Approval | Limit in workspace currency; FX invoice-date comparison; self-approval threshold enforced; critical-field change revokes; approval works with no provider |
| Xero sync | No bill before approval; tenant header correct; one POST; retry after timeout adopts existing bill; 5xx retried; 4xx stops; tokens encrypted |
| QuickBooks sync | No bill before approval; realm correct; one POST; duplicate audit behavior matches the new contract; currency is not forced to USD |
| Sage sync | Capability verified; correct business-selection header; one Purchase Transactions POST; no excluded resource called; credit-note behavior where verified; timeout reconciliation; currency decision respected |
| Sage boundary | Adapter calls only User Accounts, Contacts, Chart of Accounts, Purchase Transactions, Status Codes & Types, Currencies, Taxes, and Settings; any call to Banking, Payments & Receipts, journals, Sales, Opening Balances, Products & Services, or Reporting fails the test |
| Provider connection | No auto-select; organization picker required; reconnect updates the same row; switch blocked with unsynced bills; one active connection per workspace |
| Foreign currency | Original amount/currency preserved; unsupported currency blocks auto-post but not manual AP; rate-required path records actor/source; no silent conversion |
| Payment export | CSV formula-injection safe; decimal formatting; tenant/role scoped; PDF totals; no bank credentials |
| Status report | Append-only; idempotent; customer-reported label; history preserved; conflict returns 409 |
| Cache | Logout clears; org switch clears; role change invalidates; membership removal invalidates; mutation invalidates queue |
| RLS | Anonymous and cross-tenant access denied on every tenant table used by the workflow |
| Recovery | Stuck bill sync, failed webhook, expired token, failed OCR, and failed export are visible and recoverable without DB edits |

### Provider evidence

Record, per provider:

- The sandbox organization/tenant/realm ID for Xero/QuickBooks, or the Sage trial business ID (not secrets).
- The exact API version and base URL.
- The successful supplier import, COA import, and bill creation result.
- The timeout/retry reconciliation result.
- The currency results for GBP, USD, and NGN (supported / requires rate / unsupported).
- The date, operator, and any provider-side configuration required.
- For Sage: **API 3.1**, the exact product/edition/version, region, verified resource-area coverage, whether the exact Start edition supports supplier purchase transactions, credit-note result where applicable, optional attachment decision, and a negative check that no excluded resource was called. Sage has no development sandbox; this evidence comes from a Sage trial business account.

No provider is marked launch-ready from unit tests alone.

## 7. Acceptance criteria

### 7.1 Platform and manual AP

- A UK or US customer can sign up, onboard, upload or forward an invoice, review it, approve it, export payment instructions, and record a customer-reported payment with **no accounting connection**.
- A Nigerian customer is not blocked from signup or the manual AP workflow by country, currency, or provider choice.
- The manual AP path is visible in the UI, not merely possible through the API.
- Invoice amounts and currencies are preserved through extraction, approval, export, and status reporting.
- No supplier payment is executed, initiated, or settled by InvoiAI.
- No feature is considered complete from mocked provider calls alone.

### 7.2 Authentication and onboarding

- Registration with first name, surname, business email, and password works end to end; mobile is optional and does not block signup.
- Six-digit email OTP verification works, including paste, auto-advance, expiry countdown, resend cooldown, attempt limit, and locked/expired recovery; signup completes with email only when SMS is unavailable.
- Google OAuth works end to end; provider tokens never reach browser storage.
- Login, logout, refresh, forgot password, and reset password work.
- Unverified users cannot reach protected business functionality; the check is server-side.
- Administrator MFA uses TOTP with recovery codes, is separate from email verification, and step-up is required for sensitive actions.
- Onboarding is a resumable wizard that collects business name, country and currency with override, industry, team size, monthly invoice volume, business type/registration status, accounting software, and optional teammate invitations/approver assignment; optional questions are skippable; answers are editable later.
- UK defaults to GBP and US to USD; the default is editable; Nigeria is not blocked by country, currency, or unavailable SMS.
- “No accounting software” and “not sure” are accepted answers.
- No company registration number, tax ID, or payment card is required to create an account, start a trial, or use manual AP.
- The onboarding invite step shows seat impact before sending, and an invitation that exceeds the seat limit is blocked server-side.
- A member with several roles counts as one seat; pending invitations and removed members do not.
- The first workspace is created atomically with the creator as owner/admin.
- Multiple users can belong to a workspace with enforced roles.
- Cross-tenant access is denied on API, storage, export, search, and worker paths.
- Logout and organization switch clear cached business data; no tokens or permission decisions persist in client storage.

### 7.3 Intake, extraction, and review

- Upload and forwarding email produce the same document record, status model, duplicate fingerprint, storage policy, and timeline.
- Unsupported, oversized, spoofed, quarantined, or malware-positive files do not enter normal processing.
- Repeated webhook delivery and cross-channel duplicates do not create duplicate documents.
- Header and line items are extracted with confidence and source evidence.
- Arithmetic, date, currency, supplier, and duplicate validation produce deterministic pass/warning/blocking outcomes.
- Suspected duplicates are reviewable and never silently deleted.
- Corrections preserve the immutable original and record actor, prior value, new value, and timestamp.
- Decimal totals are exact; no floating-point money arithmetic.
- NGN and other non-GBP/USD amounts are preserved exactly.
- At the quota limit, only new AI/OCR extraction pauses; all other work continues.

### 7.4 Vendors, COA, POs, receipts, and matching

- Suppliers and chart of accounts import idempotently from the connected provider.
- The COA sync is provider-dispatched, not hardcoded to QuickBooks.
- A manual vendor and seeded starter COA work when no provider is connected.
- GL coding uses active, postable accounts and requires human approval.
- Two-way and three-way matching work with partial invoices and partial deliveries.
- An invoice may reference zero, one, or many POs/receipts.
- Line-level allocations persist and prevent over-allocation.
- Tolerances are configurable and enforced.
- A mismatch blocks approval unless an authorized approver waives it with a reason and audit event.
- A successful match never auto-approves.
- A PO change after allocation flags the match without rewriting it.
- Allocated receipts are voidable only with a reason and audit event.
- Provider PO capability is shown accurately:
  - Xero PO import works.
  - QuickBooks PO import is either verified or explicitly marked unavailable.
  - Sage Accounting shows that PO sync is not part of the agreed scope, and manual/CSV POs work.

### 7.5 Approval

- Approval limits are enforced in workspace currency.
- Foreign-currency invoices use the invoice-date rate for limit comparison and are flagged for FX review.
- The submitter cannot approve above the configured self-approval threshold.
- Owner/admin self-approval below the threshold is allowed and audited.
- Any critical-field change after approval revokes approval and requires reapproval.
- Match and coding exceptions block approval unless validly waived.
- Overdue steps escalate; delegations expire.
- Approval history records actor, time, amount, currency, authority, decision, and reason.
- Approval works with no accounting connection.

### 7.6 Accounting connection — common

- The integrations page lists Xero, QuickBooks Online, and Sage as MVP accounting choices, with accurate availability.
- The OAuth callback never selects the first organization automatically.
- The administrator must confirm the organization/tenant/realm/business.
- The connected organization name and status are visible.
- Last successful sync and last error are visible.
- Reconnect updates the same connection row and does not duplicate it.
- Switching organization or provider requires confirmation, MFA step-up, and a check for in-flight or unsynced bills.
- At most one active accounting connection exists per workspace at launch.
- Tokens remain encrypted and are never returned or logged.
- Disconnecting does not delete local records and does not void provider bills.
- Provider capability differences are shown in the UI, including PO and currency support.

### 7.7 Xero

- The administrator selects the correct Xero tenant during connection; the app never silently picks the first one.
- The `xero-tenant-id` header is correct on every request.
- Supplier, COA, and PO import commands work and are idempotent.
- No Xero bill is created before approval and permission checks.
- An approved bill is created with the original supplier, amounts, currency, dates, lines, and account codes.
- Retries cannot create a duplicate bill; a timeout reconciles to the existing bill.
- Failed sync remains visible and retryable; no database patch is required.
- The local record stores the Xero bill ID and sync history.
- Unsupported-currency invoices are blocked from auto-post with a visible reason and remain manually approvable/exportable.
- Tokens remain encrypted and are never returned or logged.
- A local void/archive does not imply the Xero bill was voided.
- A Xero sandbox proof is recorded before launch.

### 7.8 QuickBooks Online

- The existing QuickBooks OAuth, realm, sync, and provider adapter are reused, not rebuilt.
- The connected company name is visible.
- The existing vendor and COA sync work; PO sync coverage is verified or explicitly marked unavailable.
- `create_bill`/`update_bill` do not force USD when the document currency is different.
- Duplicate protection is audited and matches the common `erp_sync_key` and `find_bill` contract.
- A timeout after create reconciles to the existing bill; ambiguity stops without a second POST.
- Failed sync remains visible and retryable.
- The local record stores the QuickBooks bill ID and sync history.
- A QuickBooks sandbox proof is recorded before launch.

### 7.9 Sage Accounting — required MVP provider

- Sage Accounting is a required MVP provider, not optional or deferred.
- The exact product/edition/version, regional availability, authorization flow, endpoints, and resource capabilities are recorded from official documentation and a **Sage trial business account on API 3.1** in a short ADR. Sage Business Cloud Accounting API has no development sandbox.
- The connector uses the verified authorization flow; it is not a “generic Sage” adapter and does not target Sage Active, Intacct, Sage 50, Sage 100, or Sage X3.
- **User Accounts:** the administrator selects the correct business after authorization; the app never auto-selects; the selected external business ID and region are stored.
- **Contacts:** supplier matching works and imports only the fields needed for AP; unnecessary personal and bank details are not copied.
- **Chart of Accounts:** active postable accounts import idempotently; an inactive account cannot be coded.
- **Purchase Transactions:** an approved supplier invoice is created once with the original supplier, reference, dates, currency, lines, account references, and existing tax references; relevant credit notes are supported only where verified.
- **Status Codes & Types:** provider type/status is read and reflected in local sync state without writing custom values.
- **Currencies:** GBP, USD, and NGN behavior is recorded as supported, rate-required, or unsupported; no silent conversion; a rate-required case needs a human-confirmed rate before retry.
- **Taxes:** existing tax references are read and mapped; InvoiAI does not determine tax, calculate tax, or file returns.
- **Settings:** only the configuration the integration needs is read.
- **Attachments:** not in the first slice; if later added, it is a verified, explicitly approved extension with a customer workflow justification.
- **Exclusions:** no call is made to Sage Banking, Payments & Receipts, bank accounts, general journal/ledger, Sales Transactions, Opening Balances, Products & Services, or Reporting; this is enforced by a negative test.
- Retries cannot create a duplicate purchase transaction; a timeout reconciles to the existing record; ambiguity stops without a second POST.
- Failed sync remains visible and retryable; the local record stores the Sage transaction ID and sync history.
- A Sage trial-business proof covering API 3.1, business selection, reads, one write, retry, duplicate prevention, currency decisions, and excluded-resource checks is recorded before launch.

### 7.10 Currency

- GB workspaces default to GBP; US workspaces default to USD; both are editable.
- NGN invoices are preserved and can complete manual AP.
- No invoice amount is silently converted to the workspace currency.
- A provider currency limitation is visible before or at sync time.
- Unsupported currency → no provider POST; invoice stays approved; manual export remains available.
- Rate-required currency → human-confirmed rate, source, and actor are recorded before retry.
- Rejected currency → retry stops; the provider reason is shown safely.
- A limit-comparison conversion is labelled and is not reused as the posting rate.
- No NGN localization or universal multi-currency claim is made.

### 7.11 Payment handoff and status

- Approved invoices become available for CSV/PDF export.
- CSV and PDF exports are organization- and role-scoped, use fixed decimal formatting, and contain no bank credentials.
- Supplier payment execution and bank integrations remain disabled.
- Authorized users can record customer-reported payment status with date, amount, reference, and note.
- The UI labels the status customer-reported, not verified.
- Status history is append-only and auditable.
- Approved, exported, and customer-reported-paid states are visibly separate.
- Export works when the accounting sync is missing, failed, or blocked by currency.

### 7.12 Frontend, caching, and accessibility

- Every workflow above has a working frontend path with loading, empty, error, and success states.
- Forms use React Hook Form and Zod; validation errors are accessible and associated with fields.
- Tables support server filtering, stable sort, pagination, keyboard row opening, and URL-persisted filters.
- Status uses text and icon as well as color.
- Desktop and mobile layouts are responsive and keyboard usable; reduced-motion is respected.
- React Query keys are organization-scoped; post-mutation invalidation works; logout and organization switch clear business data.
- BFF and authenticated responses use `no-store`; sensitive data is never cached on a shared CDN.
- The integrations page shows all three providers, organization selection, status, capabilities, and currency limitations.
- The manual no-connection path is visible and usable.
- Personal finance is disabled and absent from business navigation; vendor portal is disabled.
- The free-tier price ID is removed; no free plan exists.

### 7.13 Operational and security

- Staging schema matches the migration chain; migrations are repeatable.
- RLS is enabled on tenant-owned tables and cross-tenant tests pass.
- Backups restore successfully; restore is tested.
- Xero, QuickBooks, Sage, Stripe, and inbound-email webhooks verify signatures, timestamps, replay, and idempotency where the provider supports them.
- Stuck workers, failed syncs, failed webhooks, and failed exports are visible with runbooks.
- CI reproduces the full test suite and no passing claim is made from an unpinned local run.
- Provider evidence is attached to the release record: Xero/QuickBooks sandbox and Sage trial business on API 3.1.

### 7.14 Pricing, seats, and trial

- Plans bundle a monthly invoice allowance and included seats; the two are displayed and enforced separately.
- The approved Solo (1), Duo (2), and Team (5) structure is shown, with additional seats available at the approved per-seat rate.
- A unique active member counts as one seat regardless of how many roles they hold.
- Pending invitations, revoked invitations, removed members, and disabled members do not consume a seat.
- The workspace shows included, used, and pending seats and the next charge estimate.
- An invitation that would exceed the seat limit is blocked server-side with a clear add-seats/remove-access message.
- Changing a role never changes the seat count.
- Downgrading below the active member count does not silently remove members; it blocks new invitations until the count fits or seats are added.
- The invoice allowance counts invoices entering the AP pipeline only; approvals, exports, sync attempts, and supplier-payment instructions do not consume it.
- Supplier-payment count never affects billing.
- A trial has a visible end date and invoice cap, starts without a card, and becomes read-only plus export if it ends without a chosen plan.
- No permanent free plan or Free price ID exists.
- UK plans display GBP and US plans display USD.
- Nigeria billing eligibility is tracked separately and does not block signup or manual AP.

### 7.15 Frontend design and accessibility

- The authenticated product uses the UI/UX Pro Max direction: restrained glass, glossy accents, and a few dimensional moments, kept off dense tables, forms, review, and approval screens.
- Invoice tables, forms, review, and approval screens are high-contrast, fast, calm, and easy to scan; no blur sits behind text or financial values.
- Transitions are purposeful and brief (roughly 150–250 ms) and respect reduced-motion.
- Lottie is used only for meaningful onboarding, success, or empty states, not for every icon, row, or money value.
- Scroll-driven storytelling appears only on the public landing/pricing journey.
- Public pricing renders the live catalog with a trial CTA and no permanent-free claim.
- Keyboard access, visible focus, labelled fields, screen-reader status text, and mobile layouts work across signup, onboarding, billing, review, and approval.
- No new 3D or animation dependency is added without a specific need; existing remote Lottie iframes are replaced or removed.
- The competing `:root` token blocks are consolidated into one semantic token layer.
- The implemented DM Sans (UI) and Playfair Display (display) pairing is preserved.

## 8. Failure and retry cases

| Case | Expected behavior | Recovery |
|---|---|---|
| OTP expired | Clear expired state; no session | Resend code; enforce cooldown |
| OTP attempts exceeded | Lock code; explain wait/resend | Resend after cooldown or contact support |
| Google email unverified | Do not link; create separate unverified account | Verify email |
| MFA lost device | Recovery code accepted once | Regenerate recovery codes after step-up |
| User loses membership | Immediate 403 on next request; seat released | Owner re-invites if seats allow |
| Invite exceeds seat limit | Invitation blocked with `SEAT_LIMIT_REACHED`; no pending seat created | Add seats or remove access |
| Downgrade below active members | Existing members keep access; new invites blocked | Remove access or add seats |
| Trial invoice cap reached | New AI/OCR paused; review, approval, sync, and export continue | Choose a plan or wait for reset |
| Trial ended without a plan | Read-only plus export; no new intake | Choose a plan |
| Billing currency unavailable | Show a clear message; do not charge in a different currency silently | Confirm region/billing eligibility |
| SMS unavailable at signup | Email OTP remains sufficient; no blocked signup | Complete email verification; add mobile later |
| Upload rejected | Per-file error; no document | Fix file and retry |
| Duplicate upload | Duplicate review with existing record link | Keep, reject, or explicit override |
| Email signature invalid | 401/400; no document | Provider retry with correct secret |
| Email replay | Idempotent no-op | None required |
| SPF/DKIM/DMARC failure | Quarantine | Human release/reject with audit |
| Malware detected | Quarantine; no OCR | Delete/quarantine; notify admin |
| OCR failure | Failed state with safe code | Retry processing |
| Extraction invalid | Blocking exception | Correct fields and revalidate |
| Unknown vendor | Blocking vendor exception | Link or create vendor |
| Duplicate candidate | Duplicate review; no auto-delete | Resolve with reason |
| COA not synced | Coding blocked with clear message | Sync COA or use seeded COA |
| Inactive account | Blocking coding exception | Choose active account |
| PO missing for two-way | Match exception | Add/link PO or change mode with authority |
| Receipt missing for three-way | Match exception | Record receipt or waive with reason |
| Over-allocation | 409; no allocation change | Adjust quantities |
| PO changed after allocation | Match review flag | Re-match or waive with reason |
| Receipt void attempted | Requires reason and audit | Confirm or cancel |
| Approval limit exceeded | 403/409 with limit context | Route to higher authority |
| Self-approval above threshold | 403 | Another approver decides |
| Critical field changed after approval | Approval revoked; back to awaiting approval | Reapprove |
| Approval step overdue | Escalation | Reassign or decide |
| Delegation expired | Decision rejected | New delegation |
| No accounting connection | Manual AP remains available; no sync action | Connect later or continue manually |
| Provider organization not selected | 409 with organization picker | Select organization |
| Provider token expired | 401/409 with reconnect action | Reconnect; retry |
| Provider 429 | Backoff using `Retry-After` | Automatic retry |
| Provider 5xx/timeout | Bounded retry; invoice stays failed/visible | Retry; reconcile |
| Provider timeout after create | Query by supplier + invoice number; adopt exactly one match | Manual reconcile if ambiguous |
| Provider duplicate ambiguous | Fail visibly; no second POST | Human reconciliation |
| Provider returns 4xx validation | Stop retrying; show safe field-level reason | Correct coding/data; retry |
| Provider organization switch with bills | Blocked until confirmation and sync check | Complete or cancel |
| Provider lacks PO API | No PO sync action; manual/CSV POs | Use manual/CSV |
| Currency unsupported | No POST; `blocked_currency`; manual AP available | Review currency/provider configuration |
| Currency rate required | No POST until human rate confirmed | Enter/confirm rate; retry |
| Currency rejected at POST | Stop retry; show safe reason | Review provider configuration |
| Sage capability unverified | Sage card shows verification state and does not imply a working sync; manual AP works | Complete official-documentation and Sage trial-business verification on API 3.1 |
| Sage edition not AP-compatible | Connection setup explains that the edition cannot handle supplier purchase transactions; do not offer it as AP-compatible | Choose a verified Sage Accounting edition or use manual AP |
| Sage resource unavailable | Show the limitation in the integrations UI; keep the affected invoice in manual AP; do not substitute an excluded resource | Narrow the Sage claim and re-check with the provider |
| Payment export failed | Error with retry; no partial file | Retry export |
| Status report duplicate | Idempotent or 409 | Show existing report |
| Quota reached | New AI/OCR paused; manual work continues | Upgrade or wait for reset |
| Cache stale after mutation | Invalidation failsafe | Refetch on focus/manual retry |
| Workspace switch | Business queries cleared | Reload active workspace data |

---

## 9. Contradictions and open decisions

These are recorded rather than silently resolved.

### Contradiction 1 — One-to-one PO matching vs roadmap matching

- **Request:** “one-invoice-to-one-PO matching.”
- **Roadmap Rounds 10–11:** an invoice may reference zero, one, or many POs/receipts; two-way and three-way matching; partial invoices/deliveries; line-level allocation.
- **Resolution in this spec:** implement the roadmap model. The narrower one-to-one model would fail the launch acceptance criteria and would not support consolidated supplier invoices.
- **Needed from product owner:** confirm the roadmap model, or explicitly narrow the launch scope and update the acceptance criteria.

### Contradiction 2 — Workspace created at signup vs onboarding collects the business name after verification

- **Request:** initial signup creates the first workspace and assigns the creator owner/admin.
- **Roadmap:** onboarding after verification collects business name, country, industry, team size, volume, business type/registration status, accounting software, and optional invitations/approver assignment.
- **Resolution in this spec:** create the workspace atomically when onboarding completes, within the same signup journey, so the workspace has valid business data and no orphaned half-tenant exists. The creator is still the owner/admin.
- **Needed from product owner:** confirm this sequencing, or require a draft workspace at signup with a later rename.

### Contradiction 3 — Cache warmth vs clear on organization switch

- **Current code comment in the AP hooks:** switching workspaces “never clears the cache” so data stays warm.
- **Roadmap Round 12 and acceptance criteria:** organization switches and logout clear cached business data.
- **Resolution in this spec:** follow the roadmap. Clear organization-scoped business queries on switch and logout. Non-sensitive UI preferences may remain.

### Contradiction 4 — Provider scope changed; the code lags

- **Current code:** QuickBooks has the only working accounting-provider adapter and is the default in the integrations UI. Xero has OAuth and inbound sync but auto-selects the first tenant, is GET-only, and has no provider adapter. Sage has only enum/domain references.
- **Roadmap:** Xero, QuickBooks Online, and Sage are all MVP choices; QuickBooks is not deferred.
- **Resolution in this spec:** implement all three behind the existing provider abstraction. Reuse QuickBooks; complete Xero; verify and build the Sage Accounting connector within the agreed AP resource areas. Do not present QuickBooks as the only provider or Sage as working before its recorded Sage trial-business evidence exists.

### Contradiction 5 — One `ap_status` field carries several meanings

- **Current code:** `ap_status` includes approval, ERP sync, and payment states; `payment_ready` is used after ERP sync.
- **Roadmap:** keep ingest/OCR/review/approval/accounting-sync/customer-reported payment status separate.
- **Resolution in this spec:** preserve the existing field for compatibility, but add separate ERP-sync and payment-report fields/views. Do not infer “paid” from “payment_ready.”

### Contradiction 6 — Migration path

- **Current source:** `backend/schema.sql` references `app/migrations`; the actual migrations live in `backend/migrations`.
- **Roadmap:** make one canonical path and reconcile staging.
- **Resolution in this spec:** `backend/migrations` is canonical; fix the manifest and verify staging before feature migrations.

### Contradiction 7 — Sage scope was broader than the agreed AP resource areas

- **Earlier spec:** treated “Sage” as a product family and offered Sage Accounting, Sage Intacct, and Sage 50 as MVP candidates.
- **Roadmap amendment:** Sage Accounting is required, limited to User Accounts, Contacts, Chart of Accounts, Purchase Transactions, Status Codes & Types, Currencies, Taxes, and relevant Settings; Attachments optional.
- **Current code:** no Sage connector exists.
- **Resolution in this spec:** Sage Accounting is the only MVP Sage product; Intacct, Sage 50, Sage 100, and X3 are removed; the spec limits Sage reads and writes to the agreed areas and records verification as the remaining gate.
- **Needed from product owner:** none on scope. Sage trial-business access and official documentation are needed to close the verification gate.

### Contradiction 8 — “Preserve every currency” vs provider posting limits

- **Roadmap:** preserve the original invoice amount and currency; do not silently convert; keep the customer able to complete the supported manual workflow.
- **Provider reality:** each provider can post only currencies its organization is configured for; some require an exchange rate; some may reject NGN.
- **Resolution in this spec:** preserve the invoice locally, attempt posting only when the provider capability is known, and fall back to visible review plus manual AP. Do not claim universal posting or NGN localization.
- **Needed from product owner:** accept that “preserve currency” does not mean “every provider can post every currency.”

### Contradiction 9 — UK/US market defaults vs current USD-only billing

- **Roadmap:** price UK plans in GBP and US plans in USD after eligibility and legal/tax review.
- **Current code:** `core/plan.py` prices are USD-centric; Stripe checkout has no region selector.
- **Resolution in this spec:** keep AP independent of billing; treat GBP/USD subscription configuration as a separate billing workstream and external verification item. Do not block AP launch on Stripe pricing.
- **Needed from product owner/finance:** billing entity, currency, tax, and Stripe eligibility.

### Contradiction 10 — Manual AP exists in code but not as a designed product path

- **Current UI:** integrations and settings are QuickBooks-centric; a customer without a connection has no clear guided path.
- **Roadmap:** customers without a connected or compatible provider must still be able to use manual AP.
- **Resolution in this spec:** make manual AP a first-class state in onboarding, dashboard, coding, approval, and export. Do not treat “no connection” as an error.

### Contradiction 11 — Public pricing advertises a permanent Free plan

- **Roadmap:** no permanent free tier; a time-limited trial is separate.
- **Current code:** `core/plan.py` still defines FREE, and the public home page shows a “Free” card with “Start free”.
- **Resolution in this spec:** remove the Free plan and Free price ID, replace the public card with the approved trial, and drive the public pricing page from the live catalog.
- **Needed from product owner:** approve the final GBP/USD prices, invoice allowances, additional-seat rate, and proration. The seat structure and trial terms are approved.

### Contradiction 12 — One long signup form vs account registration plus resumable onboarding

- **Product-owner direction:** short registration step followed by a resumable business-onboarding flow.
- **Current code:** `/signup` collects email and password only, and `/workspace` handles partial business creation; there is no `/onboarding` route or draft persistence.
- **Resolution in this spec:** build the two-stage flow in 5.7. Registration collects identity and credentials; onboarding collects business, team, accounting, and optional invitation/approver answers and can resume.
- **Needed from product owner:** approve the required/deferred field classification.

### Contradiction 13 — Link-based verification vs six-digit OTP

- **Roadmap:** six-digit email OTP.
- **Current code:** `/verify-email` instructs the user to click an email link.
- **Resolution in this spec:** make six-digit email OTP the target; keep link verification only as a migration alias if needed. SMS remains optional.
- **Needed from product owner:** confirm the SMS decision separately; it does not block email OTP.

The contradictions above are resolved in this spec. The subsections below list what still needs a decision, what the provider test environments need, what live launch needs, and which questions only the providers or qualified advisers can answer.

#### 9.0 Decisions requiring confirmation

| Decision | Why it matters | Blocking? | Owner |
|---|---|---|---|
| Sage capability verification (product/edition/version, region, auth, endpoints, resource shapes, credit notes, attachments) | Determines how the fixed Sage scope is implemented and what can be claimed; it does not change the scope | Yes for Sage sync; no for manual AP | Engineering |
| Sage attachment sync | Optional; keep out of the first slice unless a verified capability and a customer workflow justify it | No | Product |
| QuickBooks duplicate/idempotency audit | Determines whether existing code is safe to extend | Yes | Engineering |
| Xero tenant/org selection and POST write | Required to close the partial Xero path | Yes | Engineering |
| Provider currency behavior (GBP/USD/NGN) | Required to avoid silent conversion and false claims | Yes | Engineering + product |
| NGN posting and localization claims | Required before marketing Nigeria readiness | Yes for claims; no for manual AP | Product |
| Self-approval threshold outside GBP | Current rule is £500; other markets need a workspace-currency equivalent | No for UK pilot; yes for US launch | Product |
| One active accounting connection per workspace | Simplifies the launch contract | Confirm | Product |
| PDF export dependency | Adds a dependency versus print-to-HTML | No | Engineering |
| MFA method | TOTP + recovery codes is proposed | Confirm | Product + security |
| Billing entity and Stripe GBP/USD configuration | Required for paid launch | Yes for billing, not for AP pilot | Finance |
| Plan structure | **Approved 2026-11-08:** Solo 1 / Duo 2 / Team 5 active seats, additional paid seats, and unique-member counting | Closed | Product owner |
| Final plan amounts | GBP/USD prices, monthly invoice allowances, additional-seat rate, and proration | Yes for billing; no for AP pilot | Product owner |
| Seat overage behavior and proration | Downgrade and invite-block behavior are defined; proration amount remains unapproved | Yes for billing | Product + finance |
| Trial terms | **Approved 2026-11-08:** 14 days, 25 processed invoices, no card at signup, read-only plus export at the end | Closed | Product owner |
| SMS OTP adoption | Adds cost, country coverage risk, and signup friction; email OTP is sufficient | No; email-only fallback is safe | Product owner + engineering |
| Referral code at launch | Only include if already supported or there is a clear launch purpose | No | Product |
| Supported Sage Accounting edition | “Sage Accounting Start (Quotes & Invoicing Only)” must not be called AP-compatible without supplier purchase-transaction proof | Yes for Sage connection UI | Engineering + product |
| Matching model confirmation | Multi-PO vs one-to-one | Confirm | Product |
| Workspace creation timing | At onboarding completion vs draft at signup | Confirm | Product |

#### 9.1 Provider-test and development environment requirements

These are needed to build and test. They are not business-formation questions, and they must not be used to block unrelated engineering work:

1. A Supabase staging/test project with the same migration chain, RLS policies, storage, and backup configuration as production.
2. A transactional-email test setup for OTP and inbound forwarding. Confirm the provider, test domain, SPF/DKIM/DMARC, inbound webhook, and cost. Postmark is the candidate for both inbound and outbound.
3. A Google OAuth test client with approved redirect URIs for local and staging.
4. Supabase Auth test configuration for six-digit OTP, expiry, resend limits, email templates, and redirect allowlist.
5. The MFA method decision needed to build: TOTP authenticator app with recovery codes (recommended) versus email OTP at login.
6. SMS-provider evaluation data if SMS OTP is considered: per-message cost, country coverage including Nigeria, delivery latency, and failure handling. Not required for email-only launch.
7. Xero sandbox credentials: app scopes, demo company, tenant limits, rate limits, multi-currency behavior, and whether supplier/PO creation is permitted.
8. QuickBooks sandbox credentials: realm setup, multi-currency, PO sync coverage, and duplicate behavior.
9. Sage developer/partner account, app registration, redirect URIs, a **Sage trial business account** (no development sandbox), resource permissions, regional endpoints, and test data. Confirm the exact product/edition/version on **API 3.1** and whether app review or partner approval is required.
10. An OpenAI test key with data-processing terms, retention, no-training configuration, and model/version logging confirmed.
11. A pinned CI environment that reproduces the full test suite.
12. Stripe test-mode access for the billing workstream only, including GBP and USD test prices, trial configuration, seat quantity, and webhook fixtures.

#### 9.2 Live customer data and paid-launch requirements

These do not block sandbox development unless a provider's access rules say otherwise, but they block accepting live customer data or charging:

1. Decide the contracting entity (Nigerian entity, UK Ltd, US LLC, or merchant of record) and obtain qualified UK/US tax advice, including UK VAT treatment, US sales tax, and invoicing.
2. Customer terms, privacy notice, data-processing agreement, subprocessor list, international-transfer safeguards, and a data-subject-request process.
3. Retention, deletion, read-only-period, and export policy approved by qualified advisers.
4. Security review, incident-response ownership, breach-notification process, and appropriate insurance.
5. Confirmed hosting region and any required data-protection assessment for UK/US operations.
6. Production app approval and terms for Xero, QuickBooks Online, and Sage, including rate limits and support expectations.
7. Stripe live-account eligibility for GBP and USD subscription billing, including entity, banking, settlement, and tax.
8. Approved plan catalog and trial terms, including any consumer-trial disclosures required in the UK or US.
9. SMS-provider terms and country coverage if SMS OTP is adopted; email-only signup must remain available.
10. Confirmation that the product does not describe itself as a payment processor, tax adviser, accounting system, or e-invoicing provider.
11. Nigeria-specific legal, tax, and billing validation before any Nigeria localization claim.
12. Pilot recruitment list, interview baseline, and willingness-to-pay measurement method.

#### 9.3 Genuine provider and legal questions

Record answers before making a launch claim:

- **Sage access:** Does Sage require partner/developer approval or app certification for the listed AP resource areas? Are Purchase Transactions writes and supplier credit-note writes permitted for a third-party app? Is Attachments available, and under what retention rules?
- **Sage edition:** Does “Sage Accounting Start (Quotes & Invoicing Only)” expose supplier purchase transactions, or only quotes and sales invoices? Which edition is AP-compatible?
- **SMS coverage:** Which provider reaches Nigeria reliably, at what per-message cost, and what fallback applies when delivery fails?
- **Sage regions and currencies:** Which product/edition is available in the UK and US, and does a Sage trial business account on API 3.1 support GBP, USD, and NGN in the way the spec assumes?
- **Sage data processing:** What subprocessor, residency, and retention terms apply to data sent through the Sage API?
- **Xero and QuickBooks production access:** What app-review, certification, or security-questionnaire steps are required before live customer data?
- **Tax boundary:** Does describing the product as “AP automation with tax extraction and mapping” create a tax-preparation or tax-filing obligation in the UK or US?
- **Nigeria:** Does serving Nigerian customers from UK/EU hosting require NDPR registration, a local representative, or additional transfer safeguards?
- **Contracts:** Do the customer terms clearly exclude payment execution, tax determination, filing, and accounting-system warranties?
- **OpenAI:** Are the data-processing terms, retention settings, and no-training configuration sufficient for customer invoice data?
- **Stripe:** Is the chosen entity eligible for GBP and USD billing, and what tax/settlement obligations follow?

---

## 10. Out of scope

- Supplier payment execution, payment initiation, bank integrations, open banking, and provider settlement/reversal.
- Automated tax determination, VAT returns, MTD filing, US sales-tax filing, or e-invoicing/fiscalization.
- Advanced FX conversion, hedging, multi-currency reporting, or silent currency conversion.
- Automatic FX rate lookup for provider posting.
- Accounts receivable.
- Multi-entity consolidation or consolidated reporting.
- Complex approval matrices, custom routing DSLs, per-department policies, and advanced delegation graphs beyond the existing limit/delegation model.
- Full procurement, purchase request authoring, sourcing, inventory integration, mobile receiving, and barcode scanning.
- Gmail or Microsoft 365 mailbox OAuth.
- Supplier self-service, vendor portal, and bank-change collection.
- Enterprise SSO/SCIM.
- Personal finance in the business workspace.
- A fourth accounting provider beyond Xero, QuickBooks Online, and Sage Accounting.
- Sage Intacct, Sage 50/50cloud, Sage 100, and Sage X3 connectors. Sage Accounting is the only MVP Sage product.
- Sage Banking, Payments & Receipts, bank-account access, general journal/ledger operations, Sales Transactions, Opening Balances, Products & Services, and Reporting.
- Sage Attachments in the first slice; optional later only with verified support and a customer workflow that justifies it.
- NGN accounting localization claims beyond verified manual AP and verified provider posting.
- A second AI provider router, a microservice split, Kafka, a new global state library, or a new search cluster.
- A permanent free tier; a time-limited trial is in scope.
- Mandatory SMS OTP as a parallel verification step, or any country-specific SMS gate.
- Requiring a company registration number or tax ID to create an account, start a trial, or use manual AP.
- Per-role seat charging or counting one member as multiple seats.
- Charging by supplier-payment count or executing supplier payments.
- Rebuilding the accounting foundation, domain models, token service, worker framework, or approval engine.

## 11. Further notes

### Implementation order

1. **Sage verification and provider evidence.** Complete 5.5, secure sandboxes for Xero and QuickBooks Online plus a Sage trial business account, and record the provider contract matrix. Do not start Sage connector implementation before the ADR is recorded. (Sage verification can run in parallel with steps 2–4, but the Sage connector cannot start before it.)
2. **Evidence and foundation:** fix CI collection, pin the environment, establish migration authority, RLS, storage quarantine, backups, monitoring, and the provider-contract test harness.
3. **Identity and onboarding:** account registration, email OTP, optional mobile/SMS evaluation, Google, MFA, sessions, verification gate, resumable onboarding wizard, workspace/membership, AP roles and invitations with seat checks, market-aware currency defaults, cache clearing. This must be usable before pilot users enter real invoices.
4. **Pricing, seats, and trial:** GBP/USD plan catalog, the approved trial configuration and seat structure, seat usage and enforcement, invoice allowance separated from seats, billing UI and public pricing. Final prices, allowances, additional-seat rate, and proration require product-owner approval; implement against approved values and keep paid checkout gated until they exist.
5. **Intake and extraction:** upload hardening, forwarding email, quarantine/scanning, cross-channel dedupe, extraction evidence, validation, review surface, NGN preservation.
6. **AP core:** vendor/COA/PO/receipt import with provider dispatch, manual fallbacks, allocations, matching, coding, exceptions, approvals, limits/SoD/reapproval.
7. **Accounting provider platform:**
   - provider-neutral connection lifecycle and organization selection,
   - QuickBooks hardening: remove USD default, audit duplicates, verify PO coverage,
   - Xero completion: tenant picker, POST/PUT client, imports, `XeroAccountingProvider`,
   - Sage Accounting connector scoped to the agreed AP resource areas,
   - common write-back worker, `erp_sync_key`, `find_bill` reconciliation, currency gate.
8. **Payment handoff:** CSV/PDF export and customer-reported status, available with or without accounting sync.
9. **Hardening and pilot:** cross-tenant tests, RLS tests, webhook replay, duplicate-bill tests across all three providers, cache tests, restore test, runbooks, 3–5 pilot firms across the supported provider set.
10. **Launch gate:** every release-acceptance item green in staging using a real Xero/QuickBooks sandbox invoice and a real Sage trial-business invoice.

The two-week spike remains mandatory before a delivery date is committed. Expand it to cover the provider set actually supported:

- approved invoice → idempotent Xero sandbox bill,
- approved invoice → idempotent QuickBooks sandbox bill,
- approved invoice → idempotent purchase invoice in the Sage trial business account on API 3.1, with no excluded resource called,
- partial receipt → PO-line allocation,
- inbound email → same document record as upload,
- NGN invoice → preserved locally and correctly blocked or posted according to the provider's verified capability,
- no-connection invoice → approved, exported, and status-reported without an accounting provider.

### Frontend surface checklist

| Surface | Required states |
|---|---|
| `/signup` | Idle, validating first name/surname/email/password/optional mobile, submitting, success-to-verification, error, Google redirect; no company/tax ID or card |
| `/verify-email` | Six-digit entry, paste, expiry countdown, resend cooldown, attempts remaining, locked, expired, success, email-only path when SMS is unavailable |
| `/login` | Idle, submitting, invalid credentials, rate limited, MFA challenge, redirect to intended route |
| `/forgot-password` | Idle, submitting, non-enumerating confirmation, rate limited |
| `/reset-password` | Validating token, expired/invalid, new password, success |
| `/onboarding` | Resumable steps with saved draft, progress, optional skip, country-aware currency default and override, business type/registration status, “no accounting software,” optional invites with seat impact and approver assignment, validation, submitting, created workspace, error |
| `/workspace` | Loading, empty, select, create, incomplete-profile redirect to onboarding, no access |
| `/pricing` (public) | Live GBP/USD catalog, Solo/Duo/Team, trial CTA, no Free plan, scroll storytelling, reduced-motion and mobile states |
| `/dashboard/billing` | Current plan, trial banner and end date, invoice allowance meter, seat meter (included/used/pending), add seats, next charge, currency, invoices, payment method/portal, cancel/renew |
| `/dashboard/settings/team` | Members, Workspace Admin/Invoice Reviewer/Approver roles, invite with seat check, pending invitations, remove access, last-owner protection |
| `/integrations` | Xero, QuickBooks, Sage cards; disconnected, authorizing, organization/business selection, connected, reconnect required, error, last sync, capabilities, currency limits, Sage verification state |
| `/integrations/[provider]/organizations` | Loading, list, selected, no organizations, error, confirmation |
| `/dashboard/ap` | Loading, empty, filters, error, next action, quota warning, manual-AP state |
| `/dashboard/upload` | Drag/drop, progress, per-file result, duplicate, quota paused |
| `/dashboard/document/[id]` | Source, header, lines, confidence, validation, duplicate, currency badge, save, processing |
| `/dashboard/document/[id]/ap-processing` | Coding, matching, allocation, exceptions, submit, provider sync state |
| `/dashboard/approvals` | Queue, overdue, detail, approve/request changes/reject, limit context |
| `/dashboard/ap/exceptions` | Filter, severity, evidence, resolve/waive |
| `/dashboard/ap/payments` | Ready, blocked, export, customer-reported status, history, manual-AP notice |
| `/dashboard/settings` | Business profile edit, saved state, permission required |
| `/dashboard/settings/accounting` | Provider status, organization, COA sync, last sync, account list, PO capability |
| `/dashboard/settings/organization-access` | Members, roles, limits, delegations, last-owner protection |

### Publishing note

No issue tracker or triage-label configuration was provided in this environment. This spec and the revised 33-ticket proposal (`docs/AP_MVP_TICKET_PROPOSAL.md`) are stored in `docs/` for review. Do not publish them until the product owner approves the breakdown and a tracker plus `ready-for-agent` label are configured. After approval, create one issue per approved ticket. Then start implementation ticket by ticket, respecting each ticket's own dependencies; do not wait for every gate below before starting work those gates do not cover. Do not claim or accept a provider slice until:

- the Sage capability verification is recorded,
- the provider currency and write-back behavior is verified in that provider's test environment (Xero/QuickBooks sandbox or Sage trial business account),
- the open decisions marked blocking for that scope are resolved,
- the product owner approves the acceptance criteria.

### Review questions

1. Confirm the roadmap matching model (multi-PO, partial allocation) over one-to-one matching.
2. Confirm workspace creation at onboarding completion rather than a draft workspace at signup.
3. Confirm TOTP + recovery codes as the administrator MFA method.
4. Confirm the one PDF-generation dependency, or accept print-optimized HTML instead.
5. Confirm the Sage AP resource-area contract and that official-documentation plus **Sage trial-business evidence on API 3.1** is the remaining Sage gate. Sage has no development sandbox.
6. Confirm the manual-AP path as a first-class product state, including “no accounting software” onboarding.
7. Confirm one active accounting connection per workspace at launch.
8. Confirm the currency fallback: unsupported provider currency blocks auto-post but not approval or payment export.
9. Confirm the self-approval threshold for non-GBP workspaces.
10. Confirm the test seams: HTTP API as the primary seam, provider-contract and RLS as narrow seams, and two browser E2E paths (connected and manual).
11. Confirm the billing workstream is separate from AP launch and does not block the pilot.
12. Confirm that “Sage in MVP” means Sage Accounting scoped to the agreed AP resource areas, with no Intacct/Sage 50 work and no broader Sage capabilities.
13. Confirm that the approved Solo (1 seat), Duo (2 seats), and Team (5 seats) structure remains the launch structure; additional paid seats and unique-member counting are recorded.
14. Approve the remaining commercial values: final GBP/USD prices, monthly invoice allowances, additional-seat rate, and proration behavior. The seat structure itself is approved.
15. Confirm that the approved trial (14 days, 25 processed invoices, no card at signup, read-only plus export at the end) remains the launch trial.
16. Confirm that a unique active member counts once regardless of roles, and that pending/removed members do not consume seats.
17. Decide whether SMS OTP is adopted as an optional recovery/second factor; confirm that email OTP alone is sufficient at launch, including in Nigeria.
18. Confirm the signup field classification in 5.7 and that company registration number and tax ID are deferred and optional.
19. Confirm that “Sage Accounting Start (Quotes & Invoicing Only)” is not offered as AP-compatible unless supplier purchase-transaction support is verified.
20. Confirm the frontend direction: UI/UX Pro Max for product surfaces, Scroll Craft for public landing/pricing only, restrained glass and limited Lottie, high-contrast AP work screens.


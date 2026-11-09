# ADR 0001 — Sage Accounting AP capability and boundary

- **Status:** Scope accepted. Documentation verification complete; trial-business
  evidence **pending external access**.
- **Date:** 2026-11-09
- **Ticket:** 1 — Sage AP capability verification and ADR
- **Target:** Sage Business Cloud Accounting API **3.1**

## Context

InvoiAI's MVP must connect Xero, QuickBooks Online, and Sage Business Cloud
Accounting. Sage differs from the other two providers in one decisive way:
there is no development sandbox. The agreed AP scope also excludes payment
execution, banking, journals, sales, opening balances, products/services and
reporting. This ADR records what is verified from official Sage documentation,
what the product boundary is, and exactly which evidence still requires a Sage
trial business account. **No production Sage code is shipped in this ticket.**

## Decision

1. The only supported Sage target is **Sage Business Cloud Accounting API 3.1**
   (product family: Sage Business Cloud Accounting / Accounting Start).
   Sage Active, Sage 50, Sage 100, and Sage Intacct are not substitutes.
2. All read/write evidence comes from a **Sage trial business account**. The
   phrase "sandbox" is not used for Sage: Sage states there is no
   demo/sandbox environment for development. Trial businesses expire after 30
   days and can be extended through Sage's Extension Request Form.
3. **Sage Accounting Start is not AP-compatible for supplier purchase
   transactions.** Sage's official "Differences between Accounting and Start"
   guide marks `POST`, `PUT`, and `DELETE` on `/purchase_invoices`,
   `/purchase_credit_notes`, and `/purchase_quick_entries` as **Accounting
   only**. Start provides sales invoicing, card payments, debtors, reporting and
   VAT; Standard adds creditors control and purchase invoicing. InvoiAI must
   detect the subscription variant (`START`, `MICRO`, `ACCOUNTS`,
   `ACCOUNTING`, `ACCOUNTING_10`) and block/qualify the connection rather than
   present Start as AP-compatible.
4. Sage is limited to the agreed AP resource areas:
   - **User Accounts** — users and businesses
   - **Contacts** — suppliers and addresses
   - **Chart of Accounts** — ledger accounts
   - **Purchase Transactions** — purchase invoices and credit notes
   - **Status Codes & Types** — invoice/credit-note statuses
   - **Currencies** — currencies and exchange rates
   - **Taxes** — tax rates and schemes
   - **Settings** — business, financial and invoice settings
   - **Attachments** — optional, checked before first-slice inclusion
5. Explicitly excluded: Banking, Payments & Receipts, bank accounts,
   journals/ledger writes, Sales Transactions, Opening Balances, Products &
   Services, and Reporting. The connector must never call those resources.
6. InvoiAI never executes a Sage payment. Purchase Transactions create/read/
   update is limited to supplier documents; payment status remains
   customer-reported.

## Verified facts (official documentation)

| Fact | Detail | Source |
|---|---|---|
| Product family and version | Sage Business Cloud Accounting and Sage Business Cloud Start; Accounting API v3.1 | Sage API Overview |
| No sandbox | "At present there is no demo/sandbox environment for development purposes." Trials are created per region and expire after 30 days | Sage API Overview / FAQ |
| Trial availability | Trial businesses: United Kingdom (Start, Standard, Plus). Canada and Ireland marked currently unavailable. US is not listed in the trial table | Sage Quick Start |
| OAuth flow | Authorization Code Flow only; three-legged user consent | Sage Authentication |
| Authorization URL | `https://www.sageone.com/oauth2/auth/central?filter=apiv3.1` | Sage Authentication |
| Scopes | `readonly` or `full_access` only. Resource-area names are **not** scopes | Sage Authentication |
| Token endpoint | `POST https://oauth.accounting.sage.com/token` (`application/x-www-form-urlencoded`, `Accept: application/json`) | Sage Authentication |
| Revoke endpoint | `POST https://oauth.accounting.sage.com/revoke` | Sage Authentication |
| Token lifetime | Access token 300 seconds (5 minutes); refresh token 31 days (2,678,400 seconds) | Sage Authentication |
| Refresh rotation | Each refresh returns a new access + refresh token; a used refresh token fails. Only one refresh may be in flight | Sage Authentication / Quick Start |
| Business selection | `GET /businesses` lists businesses; `GET /businesses/lead` returns the lead business; `X-Business: <business_id>` selects context on every later request. Omitting it uses the lead business | Sage Multi Business |
| Business ID stability | The business GUID is the stable external organization identifier and must be stored with the connection | Sage Multi Business |
| Identifier exception | `/businesses` and `/user` responses do not carry an `X-Business` response header | Sage Multi Business |
| Callback registration | At least one callback URL, up to 100; HTTPS required except local hosts; callback URLs are case-sensitive and must match exactly | Sage App Registration / Quick Start |
| Rate limits | 1,296,000 requests per app per day; 150 concurrent; HTTP 429 means back off | Sage API Overview |
| Start purchase restriction | Purchase invoice/credit-note/quick-entry POST/PUT/DELETE are Accounting only | Sage Accounting vs Start |
| CSRF/PKCE | `state` recommended; PKCE `S256` optional | Sage Authentication |

### Host probe (documentation corroboration)

On 2026-11-09, an unauthenticated `GET https://api.accounting.sage.com/v3.1`
returned **HTTP 401 Unauthorized**, confirming that the v3.1 API path is live
and requires a bearer token. Probes of `/v3.1/businesses`,
`/v3.1/contacts`, `/v3.1/purchase_invoices`, and `/v3.1/user/accounts` also
returned 401. A 401 does not by itself prove an endpoint exists behind
authentication, so endpoint-level shapes remain trial-business evidence.

## Still required from the Sage trial business account

These are external and cannot be produced locally. Complete them with a Sage
UK trial business on API 3.1 (Standard or Plus so purchase transactions are
available) and the registered app credentials.

- [ ] Developer app created; callback URL registered; `client_id` and
      `client_secret` stored server-side only.
- [ ] Three-legged authorization completed; access/refresh tokens obtained and
      refreshed once, proving rotation and 5-minute expiry behaviour.
- [ ] `GET /businesses` and `GET /businesses/lead` responses captured; a
      non-lead business selected with `X-Business` and used for a read.
- [ ] `GET /user` (User Accounts) response captured.
- [ ] `GET /contacts`, `GET /ledger_accounts`, `GET /purchase_invoices`,
      `GET /purchase_credit_notes`, status, currency, tax and settings list
      shapes captured with sample responses.
- [ ] One supplier purchase invoice created with `POST /purchase_invoices`,
      read back, and updated with `PUT`.
- [ ] Purchase credit-note create/read/update proven, or explicitly marked
      unavailable for the tested variant.
- [ ] GBP, USD, and NGN currency results recorded as supported,
      rate-required, or unsupported.
- [ ] Optional Attachments capability checked; first-slice include/exclude
      decision recorded.
- [ ] Whether the app requires Sage partner/app review before production
      recorded from the developer portal.
- [ ] Variant detection proven against a Start business: the connection must
      be blocked from purchase write-back with a typed unsupported-capability
      error.

Until the list above is complete, the Sage connector is **implemented but not
accepted**, and ticket 28/29 acceptance cannot be claimed.

## Consequences

- Ticket 2's harness must include a negative assertion that Sage never calls
  Banking, Payments & Receipts, journals, Sales, Opening Balances, Products &
  Services, or Reporting endpoints.
- Ticket 24 must store the Sage business ID as the external organization
  identifier and send `X-Business` on every request.
- Ticket 28 must not expose Sage until the trial-business reference reads are
  recorded.
- Ticket 29 must gate purchase write-back on variant/capability and must not
  treat Start as AP-compatible.
- Token refresh needs a single-flight lock: concurrent refreshes with a rotated
  refresh token will fail.

## Sources

- [Sage API Overview](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/overview)
- [Sage Authentication](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/authenticating/authentication)
- [Sage Frequently Asked Questions](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/faq)
- [Sage Quick Start — Set up the Basics](https://developer.sage.com/accounting/docs/v1.0.0/guides/quick-start/getting-started)
- [Sage Multi Business](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/multi-business)
- [Sage — Differences between Accounting and Start](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/differences-between-accounting-and-start)
- [Sage — How to Create Your First App](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/getting-started/client_app_registration)

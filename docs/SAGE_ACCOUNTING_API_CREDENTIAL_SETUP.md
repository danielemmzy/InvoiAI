# Sage Business Cloud Accounting API 3.1: app credentials and business authorization

Research note — 2026-11-08. Sources below are official Sage Developer Portal documentation.

## Developer app setup

1. Sign up for a Sage developer account and create an app in the developer portal. Supply an app name and contact email; homepage URL is optional. The app name is shown to Sage Accounting users during authorization.
2. Register one or more **Callback URLs** on the app (up to 100, at least one required). Sage redirects the authorizing user to one of these URLs after they allow or deny access. Sage requires HTTPS except for local hosts, where HTTP is allowed. After saving, open the app details to reveal its `client_id` and `client_secret`. These are the app's OAuth credentials; do not treat them as a customer's Sage login or authorization. [Sage: How to Create Your First App](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/getting-started/client_app_registration)

## What “callback base URL” should mean here

The Sage guide asks for a **callback URL**, not a separate callback-base-URL field. Register the actual URL at which this application handles the OAuth return, including its callback path (for example, `https://app.example.com/oauth/sage/callback`). The OAuth redirect URI must be one of the registered callback URLs; keep the exact URI consistent in the flow. For local development, Sage permits `http://` for local hosts. Sage's guide does not prescribe a particular hostname, route, or a globally shared callback URL; those must match the application's own reachable callback handler. [Sage: app registration](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/getting-started/client_app_registration)

## Sandbox and testing

Sage explicitly says the Accounting API has **no demo/sandbox environment for development**. Its docs say to create trial Sage Business Cloud Accounting/Start accounts for each region being integrated with; trials are described as expiring after 30 days. Thus, a trial business account is the documented test target, not a separate v3.1 sandbox API or sandbox set of app credentials. [Sage: API Overview and FAQ](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/overview?tab=A)

## App credentials vs. customer consent

The `client_id` and `client_secret` identify the **integrating application** and let it participate in OAuth token exchange. By themselves, they do not authorize access to any Sage business. The Accounting API requires a valid access token, obtained through OAuth 2.0 by authenticating the app with a valid Sage business user. Sage describes this as three-legged OAuth: the business user interacts with Sage and grants the client access to that business's data without sharing their Sage credentials. The resulting access token is what accompanies API requests. [Sage: API Overview](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/overview?tab=A) [Sage: app registration](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/getting-started/client_app_registration)

In practical terms, developer registration creates reusable app-level identity; each customer/business connection still needs the Sage user's interactive sign-in and consent. Registering an app does not grant consent for a customer, and customer consent does not create the developer app credentials.

## Sources

- [Sage Accounting API Overview (v1.0.0 docs; includes v3.1 product support and no-sandbox FAQ)](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/key-concepts/overview?tab=A)
- [Sage Accounting: How to Create Your First App](https://developer.sage.com/accounting/docs/v1.0.0/guides/learning/getting-started/client_app_registration)

# Google sign-in setup

Google sign-in uses Supabase Auth's hosted Google provider and returns an
authorization code to the Next.js callback. The callback exchanges the code
server-side with its one-use PKCE verifier, then stores Supabase session tokens
only in the existing encrypted, HTTP-only BFF cookie. Google provider tokens are
not returned to the browser.

## Supabase and Google configuration

1. In Supabase Auth, enable the Google provider and enter the OAuth client ID and
   secret from the Google Cloud OAuth client. Do not reuse the Google Sheets
   integration credentials unless that OAuth client is explicitly configured
   for this auth flow.
2. In Google Cloud, add the Supabase project's callback URL
   (`https://<project-ref>.supabase.co/auth/v1/callback`) as an authorized
   redirect URI for the Google OAuth client.
3. In Supabase Auth URL configuration, allow callback URLs with the dynamic
   state query for each environment, for example
   `http://localhost:3000/api/auth/google/callback*` and
   `https://app.example.com/api/auth/google/callback*`. Also allow the password
   recovery URL ending in `/reset-password`.
4. Set the backend `FRONTEND_APP_URL`/`frontend_app_url` to the exact app origin
   used by that environment. The OAuth start endpoint rejects callback URLs
   whose origin differs from this setting.
5. Set the existing backend Supabase URL and anon key, the frontend
   `BACKEND_API_URL`, and `BFF_SESSION_SECRET` (at least 32 characters). No new
   provider secrets are required in the frontend.

Supabase Auth creates and validates the provider-side OAuth state and OIDC
nonce. The app adds a separate state cookie and PKCE verifier, checks the state
on callback, and clears both cookies after success, denial, or failure. Supabase
automatically links a matching email identity only when the existing email is
confirmed; the API also refuses to issue an app session for an unverified
resulting user.

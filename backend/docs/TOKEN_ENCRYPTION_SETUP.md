# OAuth Token Encryption Setup

`TOKEN_ENCRYPTION_KEY` is required by `TokenService` for QuickBooks/Xero OAuth
credentials. It must decode from base64url to exactly 32 bytes for AES-256-GCM.

## Generate it

From the backend root:

```powershell
python scripts/generate_token_encryption_key.py
```

For local development, the script can write it directly into `.env`:

```powershell
python scripts/generate_token_encryption_key.py --write-env
```

The script replaces an existing `TOKEN_ENCRYPTION_KEY` entry rather than
creating duplicate entries.

## Production

Do **not** put a production key into `.env.example` or source control. Generate
one once, store it in your deployment secret manager, and keep a secure backup.
Changing it without a key-rotation procedure makes existing encrypted OAuth
tokens undecryptable.

Required environment variable:

```text
TOKEN_ENCRYPTION_KEY=<generated-base64url-32-byte-key>
```

from urllib.parse import urlencode, urlparse


def build_google_authorization_url(
    *,
    supabase_url: str,
    anon_key: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    allowed_origin: str | None = None,
) -> str:
    """Build a Supabase hosted Google OAuth authorization URL."""
    redirect = urlparse(redirect_uri)
    if (
        redirect.scheme not in {"http", "https"}
        or not redirect.netloc
        or redirect.path != "/api/auth/google/callback"
        or redirect.query
        or redirect.fragment
        or redirect.username
        or redirect.password
    ):
        raise ValueError("Invalid OAuth redirect URI.")

    if allowed_origin:
        allowed = urlparse(allowed_origin)
        if (
            redirect.scheme != allowed.scheme
            or redirect.netloc != allowed.netloc
        ):
            raise ValueError("Invalid OAuth redirect URI.")

    if not all((state, code_challenge, anon_key)):
        raise ValueError("OAuth parameters are required.")

    callback = redirect_uri
    separator = "&" if "?" in callback else "?"
    callback = f"{callback}{separator}{urlencode({'state': state})}"
    base = supabase_url.rstrip("/")
    query = urlencode(
        {
            "apikey": anon_key,
            "provider": "google",
            "flow_type": "pkce",
            "redirect_to": callback,
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
        }
    )
    return f"{base}/auth/v1/authorize?{query}"

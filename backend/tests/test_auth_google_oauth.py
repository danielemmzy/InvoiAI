from urllib.parse import parse_qs, urlparse

from app.services.auth.google_oauth import build_google_authorization_url


def test_google_authorization_uses_pkce_state_and_nonce():
    url = build_google_authorization_url(
        supabase_url="https://example.supabase.co",
        anon_key="anon-key",
        redirect_uri="https://app.example.com/api/auth/google/callback",
        state="state-value",
        code_challenge="challenge-value",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.path == "/auth/v1/authorize"
    assert query["provider"] == ["google"]
    assert query["flow_type"] == ["pkce"]
    assert query["redirect_to"] == ["https://app.example.com/api/auth/google/callback?state=state-value"]
    assert "state" not in query
    assert query["code_challenge"] == ["challenge-value"]
    assert query["code_challenge_method"] == ["s256"]


def test_google_authorization_rejects_non_https_redirect_outside_local_dev():
    try:
        build_google_authorization_url(
            supabase_url="https://example.supabase.co",
            anon_key="anon-key",
            redirect_uri="https://attacker.example/callback",
            state="state-value",
            code_challenge="challenge-value",
            allowed_origin="https://app.example.com",
        )
    except ValueError as exc:
        assert str(exc) == "Invalid OAuth redirect URI."
    else:
        raise AssertionError("untrusted redirect URI must be rejected")


def test_google_authorization_rejects_other_paths_on_trusted_origin():
    try:
        build_google_authorization_url(
            supabase_url="https://example.supabase.co",
            anon_key="anon-key",
            redirect_uri="https://app.example.com/redirect?to=https://attacker.example",
            state="state-value",
            code_challenge="challenge-value",
            allowed_origin="https://app.example.com",
        )
    except ValueError as exc:
        assert str(exc) == "Invalid OAuth redirect URI."
    else:
        raise AssertionError("unapproved redirect path must be rejected")

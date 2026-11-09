-- App-owned recovery codes are only stored as high-entropy SHA-256 hashes.
-- Supabase Auth remains the authority for TOTP factors and AAL2 JWTs.
CREATE TABLE IF NOT EXISTS public.auth_mfa_recovery_codes (
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code_hash text NOT NULL CHECK (code_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, code_hash)
);

CREATE TABLE IF NOT EXISTS public.auth_mfa_recovery_step_ups (
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id uuid NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_mfa_recovery_step_ups_expiry
    ON public.auth_mfa_recovery_step_ups (expires_at);

ALTER TABLE public.auth_mfa_recovery_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_mfa_recovery_step_ups ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.auth_mfa_recovery_codes FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.auth_mfa_recovery_step_ups FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.auth_mfa_recovery_codes TO service_role;
GRANT ALL ON public.auth_mfa_recovery_step_ups TO service_role;

CREATE OR REPLACE FUNCTION public.replace_auth_mfa_recovery_codes(
    p_user_id uuid,
    p_code_hashes text[]
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF cardinality(p_code_hashes) <> 10
        OR (SELECT count(DISTINCT value) FROM unnest(p_code_hashes) AS value) <> 10
        OR EXISTS (
            SELECT 1 FROM unnest(p_code_hashes) AS value
            WHERE value !~ '^[0-9a-f]{64}$'
        ) THEN
        RAISE EXCEPTION 'exactly ten unique recovery-code hashes are required';
    END IF;

    DELETE FROM public.auth_mfa_recovery_codes WHERE user_id = p_user_id;
    INSERT INTO public.auth_mfa_recovery_codes (user_id, code_hash)
    SELECT p_user_id, value FROM unnest(p_code_hashes) AS value;
END;
$$;

CREATE OR REPLACE FUNCTION public.consume_auth_mfa_recovery_code(
    p_user_id uuid,
    p_session_id uuid,
    p_code_hash text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    consumed integer;
BEGIN
    DELETE FROM public.auth_mfa_recovery_codes
    WHERE user_id = p_user_id AND code_hash = p_code_hash;
    GET DIAGNOSTICS consumed = ROW_COUNT;

    IF consumed = 0 THEN
        RETURN false;
    END IF;

    INSERT INTO public.auth_mfa_recovery_step_ups (user_id, session_id, expires_at)
    VALUES (p_user_id, p_session_id, now() + interval '5 minutes')
    ON CONFLICT (user_id, session_id)
    DO UPDATE SET expires_at = EXCLUDED.expires_at, created_at = now();

    RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION public.replace_auth_mfa_recovery_codes(uuid, text[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.consume_auth_mfa_recovery_code(uuid, uuid, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.replace_auth_mfa_recovery_codes(uuid, text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.consume_auth_mfa_recovery_code(uuid, uuid, text) TO service_role;

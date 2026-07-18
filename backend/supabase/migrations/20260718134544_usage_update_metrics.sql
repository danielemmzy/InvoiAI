CREATE OR REPLACE FUNCTION usage_update_metrics(
    p_org_id uuid,
    p_month text,
    p_document_increment integer DEFAULT 0,
    p_storage_increment bigint DEFAULT 0,
    p_ai_tokens_increment bigint DEFAULT 0,
    p_api_calls_increment integer DEFAULT 0,
    p_ai_cost_increment numeric DEFAULT 0,
    p_user_id uuid DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN

    UPDATE usage
    SET
        document_count = document_count + p_document_increment,

        storage_bytes = storage_bytes + p_storage_increment,

        ai_tokens_used = ai_tokens_used + p_ai_tokens_increment,

        api_calls = api_calls + p_api_calls_increment,

        ai_cost_usd = ai_cost_usd + p_ai_cost_increment,

        last_document_at = CASE
            WHEN p_document_increment > 0 THEN now()
            ELSE last_document_at
        END,

        last_document_by = CASE
            WHEN p_document_increment > 0 THEN p_user_id
            ELSE last_document_by
        END,

        last_ai_request_at = CASE
            WHEN p_ai_tokens_increment > 0 THEN now()
            ELSE last_ai_request_at
        END,

        last_ai_request_by = CASE
            WHEN p_ai_tokens_increment > 0 THEN p_user_id
            ELSE last_ai_request_by
        END,

        last_api_request_at = CASE
            WHEN p_api_calls_increment > 0 THEN now()
            ELSE last_api_request_at
        END,

        last_api_request_by = CASE
            WHEN p_api_calls_increment > 0 THEN p_user_id
            ELSE last_api_request_by
        END

    WHERE
        org_id = p_org_id
        AND month = p_month;

END;
$$;
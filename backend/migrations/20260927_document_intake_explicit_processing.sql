-- Upload is storage-only. Human acceptance and AI processing are separate states.
ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS human_review_status text NOT NULL DEFAULT 'pending';

ALTER TABLE public.documents
    DROP CONSTRAINT IF EXISTS chk_documents_human_review_status;

ALTER TABLE public.documents
    ADD CONSTRAINT chk_documents_human_review_status
    CHECK (human_review_status IN ('pending','accepted','declined'));

ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS intelligence_status text NOT NULL DEFAULT 'not_requested';

ALTER TABLE public.documents
    DROP CONSTRAINT IF EXISTS chk_documents_intelligence_status;

ALTER TABLE public.documents
    ADD CONSTRAINT chk_documents_intelligence_status
    CHECK (intelligence_status IN ('not_requested','queued','processing','complete','failed'));

CREATE INDEX IF NOT EXISTS ix_documents_org_human_review_status
    ON public.documents(org_id, human_review_status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_documents_org_intelligence_status
    ON public.documents(org_id, intelligence_status, created_at DESC);

-- Preserve the state of documents that were already processed before this split.
UPDATE public.documents
SET human_review_status = 'accepted'
WHERE human_review_status = 'pending'
  AND (status = 'approved' OR ap_enabled = true);

UPDATE public.documents d
SET intelligence_status = 'complete'
WHERE d.intelligence_status = 'not_requested'
  AND EXISTS (
      SELECT 1
      FROM public.document_analyses a
      WHERE a.document_id = d.id
  );

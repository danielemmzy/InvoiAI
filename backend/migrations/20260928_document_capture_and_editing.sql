ALTER TABLE public.documents
  ADD COLUMN IF NOT EXISTS capture_status text NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS capture_progress integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS capture_error text,
  ADD COLUMN IF NOT EXISTS capture_overrides jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.documents DROP CONSTRAINT IF EXISTS chk_documents_capture_status;
ALTER TABLE public.documents ADD CONSTRAINT chk_documents_capture_status
  CHECK (capture_status IN ('pending','processing','complete','failed'));

CREATE INDEX IF NOT EXISTS ix_documents_org_capture_status
  ON public.documents(org_id, capture_status, created_at DESC);

UPDATE public.documents d
SET capture_status = 'complete', capture_progress = 100
WHERE d.capture_status = 'pending'
  AND EXISTS (SELECT 1 FROM public.ocr_results o WHERE o.document_id = d.id);

-- Optional review/edit history is recorded in the existing immutable audit_logs table.

-- Deterministic correction for obvious manually uploaded PO files that
-- were previously stored as invoice before intake recognition was added.
-- This does not run OCR or AI and only changes records with strong PO signals.

UPDATE public.documents
SET
  document_type = 'purchase_order',
  workflow_route = 'procurement'
WHERE source = 'manual'
  AND document_type = 'invoice'
  AND (
    lower(coalesce(file_name, '')) ~ 'purchase[ _-]*order'
    OR lower(coalesce(document_number, '')) ~ '^p\.?o\.?[ _#.:/-]*[0-9]+'
  );

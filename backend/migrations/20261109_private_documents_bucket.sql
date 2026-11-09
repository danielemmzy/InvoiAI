-- Uploaded invoices must never be readable through a public bucket URL.
-- If this migration runs before bucket provisioning, provision the bucket
-- as private in the Supabase project configuration before accepting uploads.
do $$
begin
    if to_regclass('storage.buckets') is not null then
        update storage.buckets
           set public = false,
               file_size_limit = 10485760,
               allowed_mime_types = array[
                   'application/pdf', 'image/jpeg', 'image/png', 'image/webp'
               ]
         where id = 'documents';
    end if;
end $$;

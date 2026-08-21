-- ADR 0046 / 0057: a source lookup key may be repeated by the source export.
-- The source UUID remains the immutable post identity; this key is searchable
-- evidence and must not reject otherwise distinct source posts.
drop index if exists source_post_source_identity_idx;

create index if not exists source_post_source_identity_lookup_idx
    on source_post (source_system_code, source_record_key)
    where source_system_code is not null and source_record_key is not null;

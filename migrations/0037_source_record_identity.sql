-- ADR 0046: preserve the opaque source identity used to import each post.
-- The deterministic post UUID remains the internal product identity; these
-- columns retain the source-system key needed for audit and board search.
alter table source_post add column if not exists source_system_code text;
alter table source_post add column if not exists source_record_key text;

create unique index if not exists source_post_source_identity_idx
    on source_post (source_system_code, source_record_key)
    where source_system_code is not null and source_record_key is not null;

create index if not exists source_post_source_record_key_trgm_idx
    on source_post using gin (lower(source_record_key) gin_trgm_ops);

comment on column source_post.source_system_code is
    'Opaque source-system namespace supplied by the importer; not an authorization scope.';
comment on column source_post.source_record_key is
    'Original source record key preserved for evidence lookup; never replaced by the internal UUID.';

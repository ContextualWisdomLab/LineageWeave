-- Keep body search indexed without duplicating the full, potentially very large
-- source body. The detail endpoint still returns the complete post_body.
create extension if not exists pg_trgm;

-- CREATE INDEX CONCURRENTLY leaves an invalid catalog row when its builder is
-- interrupted. IF NOT EXISTS would then skip that unusable object forever.
-- Drop only this migration's invalid owned indexes, outside a transaction,
-- before replaying the normal idempotent creates.
select format('drop index concurrently if exists %I.%I', namespace.nspname, class.relname)
from pg_index index_state
join pg_class class on class.oid = index_state.indexrelid
join pg_namespace namespace on namespace.oid = class.relnamespace
where namespace.nspname = 'public'
  and class.relname in (
      'source_post_body_prefix_trgm_idx',
      'source_post_body_fts_idx'
  )
  and not index_state.indisvalid
\gexec

create index concurrently if not exists source_post_body_prefix_trgm_idx
    on source_post using gin (
        lower(left(coalesce(post_body, ''), 16384)) gin_trgm_ops
    );

create index concurrently if not exists source_post_body_fts_idx
    on source_post using gin (
        to_tsvector('simple', coalesce(post_body, ''))
    );

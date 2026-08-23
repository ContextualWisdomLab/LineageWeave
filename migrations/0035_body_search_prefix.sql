-- Keep body search indexed without duplicating the full, potentially very large
-- source body. The detail endpoint still returns the complete post_body.
set client_min_messages = warning;

create extension if not exists pg_trgm;

-- A canceled CREATE INDEX CONCURRENTLY leaves an unusable index whose name
-- still makes IF NOT EXISTS skip the repair on the next migration run.
do $$
begin
    if exists (
        select 1
          from pg_index index_state
          join pg_class index_class on index_class.oid = index_state.indexrelid
         where index_class.relname = 'source_post_body_prefix_trgm_idx'
           and not index_state.indisvalid
    ) then
        drop index source_post_body_prefix_trgm_idx;
    end if;
end $$;

create index concurrently if not exists source_post_body_prefix_trgm_idx
    on source_post using gin (
        lower(left(coalesce(post_body, ''), 16384)) gin_trgm_ops
    );

do $$
begin
    if exists (
        select 1
          from pg_index index_state
          join pg_class index_class on index_class.oid = index_state.indexrelid
         where index_class.relname = 'source_post_body_fts_idx'
           and not index_state.indisvalid
    ) then
        drop index source_post_body_fts_idx;
    end if;
end $$;

create index concurrently if not exists source_post_body_fts_idx
    on source_post using gin (
        to_tsvector('simple', left(coalesce(post_body, ''), 16384))
    );

-- Keep body search indexed without duplicating the full, potentially very large
-- source body. The detail endpoint still returns the complete post_body.
set client_min_messages = warning;

create extension if not exists pg_trgm;

create index concurrently if not exists source_post_body_prefix_trgm_idx
    on source_post using gin (
        lower(left(coalesce(post_body, ''), 16384)) gin_trgm_ops
    );

create index concurrently if not exists source_post_body_fts_idx
    on source_post using gin (
        to_tsvector('simple', left(coalesce(post_body, ''), 16384))
    );

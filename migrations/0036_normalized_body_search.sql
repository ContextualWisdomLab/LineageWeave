-- Search rendered post text, never arbitrary bytes inside an embedded image.
set client_min_messages = warning;

create or replace function source_post_search_text(body text)
returns text
language sql
immutable
parallel safe
as $$
    select left(
        regexp_replace(
            regexp_replace(
                regexp_replace(coalesce(body, ''), '<img[^>]*>', ' ', 'gi'),
                '<[^>]+>', ' ', 'g'
            ),
            '\s+', ' ', 'g'
        ),
        16384
    )
$$;

create index if not exists source_post_search_prefix_trgm_idx
    on source_post using gin (
        lower(left(source_post_search_text(post_body), 16384)) gin_trgm_ops
    );

create index if not exists source_post_search_fts_idx
    on source_post using gin (
        to_tsvector('simple', source_post_search_text(post_body))
    );

drop index if exists source_post_body_prefix_trgm_idx;
drop index if exists source_post_body_fts_idx;

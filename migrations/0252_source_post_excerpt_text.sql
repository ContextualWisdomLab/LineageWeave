-- ADR 0053 amendment: return the same normalized 420-character excerpt
-- without regex-normalizing an entire large source body. Replay-safe.
create or replace function source_post_excerpt_text(body text, max_chars integer)
returns text
language sql
immutable
parallel safe
as $$
    select case
        when body is null or char_length(substr(body, 1, 16385)) <= 16384
            then btrim(left(source_post_search_text(body), max_chars))
        else coalesce(
            (select btrim(left(prefix.normalized, max_chars))
               from (select source_post_search_text(
                                regexp_replace(substr(body, 1, 16384), '<[^>]*$', '')
                            ) as normalized) prefix
              where char_length(prefix.normalized) >= max_chars),
            btrim(left(source_post_search_text(body), max_chars))
        )
    end
$$;

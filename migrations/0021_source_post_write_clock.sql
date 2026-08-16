-- Keep source_post.updated_at as the live write clock (ADR 0016 / 0021).
--
-- A title or body rewrite bumps the clock unless the same statement
-- already assigned updated_at. That lets `make seed` pin Demo public
-- post to 2026-01-13 while a later product edit still marks the title
-- updated after cutoff. Thread-group or visibility-only updates do
-- not pretend to be a rewrite.

begin;

create or replace function touch_source_post_write_clock()
returns trigger
language plpgsql
as $$
begin
    if (new.post_title, new.post_body) is distinct from (old.post_title, old.post_body)
       and new.updated_at is not distinct from old.updated_at then
        new.updated_at := clock_timestamp();
    end if;
    return new;
end;
$$;

comment on function touch_source_post_write_clock() is
    'Bumps source_post.updated_at when title or body changes unless the '
    'statement already assigned updated_at.';

drop trigger if exists source_post_write_clock on source_post;
create trigger source_post_write_clock
    before update on source_post
    for each row
    execute function touch_source_post_write_clock();

comment on trigger source_post_write_clock on source_post is
    'Live write clock for analysis-run cutoff comparison (ADR 0016).';

commit;

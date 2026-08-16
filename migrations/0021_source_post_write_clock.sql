-- Keep source_post.updated_at as the live write clock (ADR 0016).
-- An explicit updated_at in the UPDATE is honored so historical seed
-- rows can keep their authoring instant. Otherwise the trigger stamps
-- now(). Two-word relation and column names stay snake_case.

create or replace function set_source_post_updated_at()
returns trigger
language plpgsql
as $$
begin
    if new.post_title is not distinct from old.post_title
       and new.post_body is not distinct from old.post_body then
        return new;
    end if;
    if new.updated_at is not distinct from old.updated_at then
        new.updated_at = now();
    end if;
    return new;
end;
$$;

drop trigger if exists source_post_set_updated_at on source_post;
create trigger source_post_set_updated_at
    before update on source_post
    for each row
    execute function set_source_post_updated_at();

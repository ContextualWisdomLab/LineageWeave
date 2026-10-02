-- Preserve one-time translation seed provenance from TRUNCATE ... CASCADE.
-- Row-level ownership/retirement guards cannot run when PostgreSQL truncates the
-- referencing ownership table as part of a ledger-root CASCADE.
begin;

create or replace function guard_ui_translation_seed_ownership_truncate()
returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    raise exception
        'UI translation seed ownership history cannot be truncated; use governed seed rollback';
end;
$$;

drop trigger if exists ui_translation_seed_ownership_truncate_guard
    on public.ui_translation_seed_ownership;
create trigger ui_translation_seed_ownership_truncate_guard
before truncate on public.ui_translation_seed_ownership
for each statement execute function guard_ui_translation_seed_ownership_truncate();

commit;

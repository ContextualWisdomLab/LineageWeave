-- Remove the seed-ownership TRUNCATE guard before the ownership table rollback.
begin;

drop trigger if exists ui_translation_seed_ownership_truncate_guard
    on public.ui_translation_seed_ownership;
drop function if exists guard_ui_translation_seed_ownership_truncate();

commit;

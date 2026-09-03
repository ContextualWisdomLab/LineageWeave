-- Reverse 0246 only while the translation-ledger foundation is still empty.
-- Once product copy exists, ADR 0362 requires application/read-routing recovery
-- rather than a destructive schema down-migration.
begin;

-- Serialize the emptiness decision with writers through transaction end. Without
-- this lock, a resource can be inserted after the guard and then erased by DROP.
lock table ui_translation_resource in access exclusive mode;

do $$
begin
    if exists (
        select 1
          from ui_translation_resource
    ) then
        raise exception 'refusing 0246 rollback because translation resources exist; use application/read-routing recovery';
    end if;
end $$;

alter table user_account
    drop constraint if exists user_account_preferred_locale_ck;

alter table user_account
    add constraint user_account_preferred_locale_ck
    check (preferred_locale is null or preferred_locale in ('en', 'ko', 'zh', 'ja', 'vi'));

drop table if exists ui_translation_text;
drop table if exists ui_translation_key;
drop table if exists ui_translation_resource;

drop function if exists guard_ui_translation_child_mutation();
drop function if exists guard_ui_translation_resource_mutation();

commit;

-- Reverse 0246 only while the translation-ledger foundation is still empty.
-- Once product copy exists, ADR 0362 requires application/read-routing recovery
-- rather than a destructive schema down-migration.
begin;

-- Serialize both rollback admission decisions with their writers through
-- transaction end. A retry after a completed rollback has no resource relation
-- left, but member-locale admission still needs to converge through the same
-- explicit guard before the pre-0246 constraint is restored.
do $$
declare
    resource_relation_exists boolean := true;
begin
    begin
        execute 'lock table ui_translation_resource in access exclusive mode';
    exception
        when undefined_table then
            resource_relation_exists := false;
    end;

    if resource_relation_exists and exists (
        select 1
          from ui_translation_resource
    ) then
        raise exception 'refusing 0246 rollback because translation resources exist; use application/read-routing recovery';
    end if;

    lock table user_account in access exclusive mode;
    if exists (
        select 1
          from user_account
         where preferred_locale is not null
           and preferred_locale not in ('en', 'ko', 'zh', 'ja', 'vi')
    ) then
        raise exception 'refusing 0246 rollback because post-0246 member locale preferences exist; migrate member preferences before schema rollback';
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

-- 0247 may already have been applied. Dropping the ledger relations removes its
-- triggers, while this function cleanup keeps a direct 0246 rollback converged
-- even when the caller did not run the optional 0247 rollback artifact first.
drop function if exists guard_ui_translation_truncate();
drop function if exists guard_ui_translation_child_mutation();
drop function if exists guard_ui_translation_resource_mutation();

commit;

-- Reverse 0246. This rollback is for the translation-ledger foundation before
-- the buyer-visible locale cutover: remove the ledger schema and restore the
-- member-locale constraint owned by ADR 0069 / migration 0044.
begin;

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

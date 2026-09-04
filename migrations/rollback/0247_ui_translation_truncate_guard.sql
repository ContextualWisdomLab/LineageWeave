-- Remove the 0247 statement-level TRUNCATE guards before rolling back 0246.
begin;

do $$
begin
    if to_regclass('public.ui_translation_resource') is not null then
        execute 'drop trigger if exists ui_translation_resource_truncate_guard on ui_translation_resource';
    end if;
    if to_regclass('public.ui_translation_key') is not null then
        execute 'drop trigger if exists ui_translation_key_truncate_guard on ui_translation_key';
    end if;
    if to_regclass('public.ui_translation_text') is not null then
        execute 'drop trigger if exists ui_translation_text_truncate_guard on ui_translation_text';
    end if;
end $$;

drop function if exists guard_ui_translation_truncate();

commit;

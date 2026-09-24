-- Restore the Customer Master-specific seed boundary after Similar VOC v1 is gone.
-- This rollback never removes a current product resource or another seed owner's
-- provenance record. A blocked/pending/retired receipt owns no resource, so the
-- generic layer can be removed while preserving any operator-owned Similar VOC v1.
begin;

do $generic_seed_ownership_rollback$
begin
    delete from public.ui_translation_seed_ownership
     where migration_key = '0249_z_similar_voc_translation_draft'
       and ownership_state in ('pending', 'blocked', 'retired')
       and resource_id is null;

    -- An owned receipt is the destructive-authority boundary. Refuse to remove
    -- the generic trigger layer until its exact owned resource has first been
    -- handled by the bounded Similar VOC rollback. Unowned operator copy is not
    -- a dependency of this migration and must survive rollback untouched.
    if exists (
        select 1
          from public.ui_translation_seed_ownership
         where migration_key = '0249_z_similar_voc_translation_draft'
    ) then
        raise exception
            'Generic UI translation seed ownership rollback refuses while Similar VOC ownership remains';
    end if;

    if exists (
        select 1
          from public.ui_translation_seed_ownership
         where migration_key <> '0248_customer_master_translation_draft'
    ) then
        raise exception
            'Generic UI translation seed ownership rollback refuses while another generic seed owner remains';
    end if;
end;
$generic_seed_ownership_rollback$;

drop trigger if exists ui_translation_seed_text_ownership_guard
    on public.ui_translation_text;
drop trigger if exists ui_translation_seed_key_ownership_guard
    on public.ui_translation_key;
drop trigger if exists ui_translation_seed_resource_ownership_bind
    on public.ui_translation_resource;
drop trigger if exists ui_translation_seed_resource_ownership_guard
    on public.ui_translation_resource;

drop trigger if exists customer_master_seed_text_ownership_guard
    on public.ui_translation_text;
create trigger customer_master_seed_text_ownership_guard
before insert or update or delete on public.ui_translation_text
for each row execute function guard_customer_master_seed_child_ownership();

drop trigger if exists customer_master_seed_key_ownership_guard
    on public.ui_translation_key;
create trigger customer_master_seed_key_ownership_guard
before insert or update or delete on public.ui_translation_key
for each row execute function guard_customer_master_seed_child_ownership();

drop trigger if exists customer_master_seed_resource_ownership_bind
    on public.ui_translation_resource;
create trigger customer_master_seed_resource_ownership_bind
after insert on public.ui_translation_resource
for each row execute function bind_customer_master_seed_resource_ownership();

drop trigger if exists customer_master_seed_resource_ownership_guard
    on public.ui_translation_resource;
create trigger customer_master_seed_resource_ownership_guard
before insert or delete on public.ui_translation_resource
for each row execute function guard_customer_master_seed_resource_ownership();

drop function if exists guard_ui_translation_seed_child_ownership();
drop function if exists bind_ui_translation_seed_resource_ownership();
drop function if exists guard_ui_translation_seed_resource_ownership();

commit;

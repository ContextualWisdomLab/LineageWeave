-- Fail-closed rollback for migration 0023.
--
-- Outbox evidence must be exported or explicitly deleted under an
-- approved retention procedure before these objects can be removed.
-- The extended purge function stays; it already guards missing tables.

begin;

do $$
declare
    relation_name text;
    relation_has_rows boolean;
begin
    foreach relation_name in array array[
        'analysis_run_outbox_delivery',
        'analysis_run_outbox'
    ] loop
        if to_regclass('public.' || relation_name) is not null then
            execute format('select exists (select 1 from %I)', relation_name)
               into relation_has_rows;
            if relation_has_rows then
                raise exception 'analysis_run_outbox_not_empty';
            end if;
        end if;
    end loop;
end
$$;

drop trigger if exists analysis_run_outbox_delivery_mutation_reject
    on analysis_run_outbox_delivery;
drop trigger if exists analysis_run_outbox_mutation_reject
    on analysis_run_outbox;
drop function if exists reject_analysis_run_outbox_delivery_mutation();
drop function if exists reject_analysis_run_outbox_mutation();
drop table if exists analysis_run_outbox_delivery;
drop table if exists analysis_run_outbox;

commit;

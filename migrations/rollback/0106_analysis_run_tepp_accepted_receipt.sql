-- Fail-closed rollback for migration 0106.
--
-- Accepted TEPP receipts are transport evidence. Export or explicitly
-- delete them under an approved retention procedure before dropping.

begin;

do $$
declare
    relation_has_rows boolean;
begin
    if to_regclass('public.analysis_run_tepp_accepted_receipt') is not null then
        execute 'select exists (select 1 from analysis_run_tepp_accepted_receipt)'
           into relation_has_rows;
        if relation_has_rows then
            raise exception 'analysis_run_tepp_accepted_receipt_not_empty';
        end if;
    end if;
end
$$;

drop index if exists analysis_run_tepp_accepted_receipt_received_idx;
drop table if exists analysis_run_tepp_accepted_receipt;

commit;

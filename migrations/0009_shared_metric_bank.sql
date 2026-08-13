-- ADR 0003 slice 5: one shared item bank across PU / team / project.
-- Widen grouping_kind so report_item_parameter can store the pooled bank.

do $$
declare
    rec record;
begin
    for rec in
        select conname
        from pg_constraint
        where conrelid = 'report_period_score'::regclass
          and contype = 'c'
          and pg_get_constraintdef(oid) like '%grouping_kind%'
    loop
        execute format('alter table report_period_score drop constraint %I', rec.conname);
    end loop;
    alter table report_period_score
        add constraint report_period_score_grouping_kind_check
        check (grouping_kind in (
            'process_unit', 'corporate_entity', 'thread_group', 'shared_metric'
        ));
end
$$;

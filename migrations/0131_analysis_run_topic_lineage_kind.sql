-- Adds the topic-lineage analysis-run kind (ADR 0147).
--
-- Requesting/starting this kind submits through the same tepp_client
-- boundary as analysis_run_tepp (ADR 0022) -- it never computes a topic
-- identity or predecessor/successor association locally. This
-- migration only registers the kind vocabulary and widens the existing
-- kind check constraints; it stores no post body and no fabricated
-- measurement.

begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('analysis_run_kind', 'analysis_run_topic_lineage', 'Topic lineage', 3)
on conflict (lookup_code) do nothing;

alter table analysis_run
    drop constraint if exists analysis_run_kind_check;
alter table analysis_run
    add constraint analysis_run_kind_check
        check (run_kind_code in (
            'analysis_run_lineage',
            'analysis_run_report',
            'analysis_run_tepp',
            'analysis_run_topic_lineage'
        ));

do $$
begin
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox
            drop constraint if exists analysis_run_outbox_kind_check;
        alter table analysis_run_outbox
            add constraint analysis_run_outbox_kind_check
                check (work_kind_code in (
                    'analysis_run_lineage',
                    'analysis_run_tepp',
                    'analysis_run_topic_lineage'
                ));
    end if;
end
$$;

commit;

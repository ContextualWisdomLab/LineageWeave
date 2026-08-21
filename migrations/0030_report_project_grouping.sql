begin;

-- secondary_grouping_key is the persisted fine-grained project key used by
-- reconstruct(). Expose it as a report dimension without collapsing it into
-- the coarser thread_group key.
alter table report_period_score
    drop constraint if exists report_period_score_grouping_kind_check;

alter table report_period_score
    add constraint report_period_score_grouping_kind_check
    check (grouping_kind in (
        'process_unit', 'corporate_entity', 'thread_group', 'team', 'project', 'shared_metric'
    ));

commit;

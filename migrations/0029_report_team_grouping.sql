begin;

-- A post may belong to multiple cataloged teams through post_team_mention.
-- Report rows keep the existing post-level score but allow that score to be
-- present in each authorized team grouping (true membership, not a guessed
-- single team assignment).
alter table report_period_score
    drop constraint if exists report_period_score_grouping_kind_check;

alter table report_period_score
    add constraint report_period_score_grouping_kind_check
    check (grouping_kind in (
        'process_unit', 'corporate_entity', 'thread_group', 'team', 'project', 'shared_metric'
    ));

comment on table report_member_score is
    'One post score per report grouping; a post may appear in multiple team groups.';

commit;

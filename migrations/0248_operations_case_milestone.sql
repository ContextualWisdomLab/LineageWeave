-- ADR 0206: observed lifecycle milestones; no inferred timestamps or delay threshold.
create table if not exists operations_case_milestone (
    post_id uuid not null,
    case_kind_code text not null,
    milestone_type_code text not null check (milestone_type_code in (
        'claim_received', 'cause_confirmed',
        'rebid_response_requested', 'rebid_decision_recorded',
        'handover_started', 'handover_accepted'
    )),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    evidence_post_id uuid not null references source_post(post_id) on delete restrict,
    evidence_input_sha256 text not null check (evidence_input_sha256 ~ '^[0-9a-f]{64}$'),
    observed_at timestamptz not null,
    time_axis_code text not null check (time_axis_code in ('event_occurred_at', 'created_at')),
    primary key (post_id, case_kind_code, milestone_type_code),
    foreign key (post_id, case_kind_code)
        references operations_case_classification(post_id, case_kind_code)
        on delete cascade
);

create table if not exists operations_case_missing_milestone (
    post_id uuid not null,
    case_kind_code text not null,
    milestone_type_code text not null check (milestone_type_code in (
        'claim_received', 'cause_confirmed',
        'rebid_response_requested', 'rebid_decision_recorded',
        'handover_started', 'handover_accepted'
    )),
    primary key (post_id, case_kind_code, milestone_type_code),
    foreign key (post_id, case_kind_code)
        references operations_case_classification(post_id, case_kind_code)
        on delete cascade
);

alter table operations_case_milestone
    drop constraint if exists operations_case_milestone_kind_type_check,
    add constraint operations_case_milestone_kind_type_check check (
        (case_kind_code = 'claim_investigation'
         and milestone_type_code in ('claim_received', 'cause_confirmed'))
        or (case_kind_code = 'rebid_handover'
            and milestone_type_code in (
                'rebid_response_requested', 'rebid_decision_recorded',
                'handover_started', 'handover_accepted'
            ))
    ) not valid;

alter table operations_case_missing_milestone
    drop constraint if exists operations_case_missing_milestone_kind_type_check,
    add constraint operations_case_missing_milestone_kind_type_check check (
        (case_kind_code = 'claim_investigation'
         and milestone_type_code in ('claim_received', 'cause_confirmed'))
        or (case_kind_code = 'rebid_handover'
            and milestone_type_code in (
                'rebid_response_requested', 'rebid_decision_recorded',
                'handover_started', 'handover_accepted'
            ))
    ) not valid;

create index if not exists operations_case_milestone_kind_time_idx
    on operations_case_milestone (case_kind_code, milestone_type_code, observed_at, post_id);

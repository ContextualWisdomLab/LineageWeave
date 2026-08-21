create table if not exists post_summary_action (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    action_ordinal integer not null,
    action_text text not null,
    requester_actor_name text,
    processor_actor_name text,
    evidence_text text not null,
    primary key (post_id, action_ordinal),
    foreign key (post_id, requester_actor_name)
        references post_summary_role (post_id, actor_name),
    foreign key (post_id, processor_actor_name)
        references post_summary_role (post_id, actor_name)
);

comment on table post_summary_action is
    'Source-grounded major event handoffs; actor names resolve through post_summary_role.';

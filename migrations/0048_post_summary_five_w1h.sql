begin;

-- Explicit source-backed dimensions that are not safely derivable from the
-- record filing timestamp, roles, or a generic key-event label.
create table if not exists post_summary_five_w1h (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    slot_code text not null check (slot_code in ('when', 'where', 'why', 'how')),
    value_ordinal integer not null check (value_ordinal >= 0),
    value_text text not null,
    evidence_text text not null,
    primary key (post_id, slot_code, value_ordinal)
);

create index if not exists post_summary_five_w1h_post_idx
    on post_summary_five_w1h (post_id, slot_code, value_ordinal);

commit;

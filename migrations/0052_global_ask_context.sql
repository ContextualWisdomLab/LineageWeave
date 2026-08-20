-- Account-owned Global Ask continuity. Evidence is always retrieved again;
-- these rows only retain conversation context and citation references.

create table if not exists global_ask_session (
    global_ask_session_id uuid primary key,
    user_account_id uuid not null references user_account (user_account_id) on delete cascade,
    context_summary text,
    context_summary_through_ordinal integer not null default 0
        check (context_summary_through_ordinal >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists global_ask_session_account_idx
    on global_ask_session (user_account_id, updated_at desc);

create table if not exists global_ask_turn (
    global_ask_session_id uuid not null
        references global_ask_session (global_ask_session_id) on delete cascade,
    turn_ordinal integer not null check (turn_ordinal > 0),
    question_text text not null,
    answer_text text not null,
    created_at timestamptz not null default now(),
    primary key (global_ask_session_id, turn_ordinal)
);

create table if not exists global_ask_turn_citation (
    global_ask_session_id uuid not null,
    turn_ordinal integer not null,
    citation_ordinal integer not null check (citation_ordinal >= 0),
    cited_post_id uuid not null references source_post (post_id) on delete cascade,
    primary key (global_ask_session_id, turn_ordinal, citation_ordinal),
    foreign key (global_ask_session_id, turn_ordinal)
        references global_ask_turn (global_ask_session_id, turn_ordinal)
        on delete cascade
);

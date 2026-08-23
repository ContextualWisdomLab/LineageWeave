-- ADR 0126: persist the account-owned Global Ask transcript.
-- Reuse the existing Global Ask session key used by the product's prior
-- context work. The API calls it conversation_id for reader-facing clarity.

create table if not exists global_ask_session (
    global_ask_session_id uuid primary key,
    user_account_id uuid not null references user_account(user_account_id) on delete cascade,
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
        references global_ask_session(global_ask_session_id) on delete cascade,
    turn_ordinal integer not null check (turn_ordinal > 0),
    question_text text not null,
    answer_text text not null,
    next_action text,
    created_at timestamptz not null default now(),
    primary key (global_ask_session_id, turn_ordinal)
);

alter table global_ask_turn add column if not exists next_action text;

create table if not exists global_ask_turn_citation (
    global_ask_session_id uuid not null,
    turn_ordinal integer not null,
    citation_ordinal integer not null check (citation_ordinal >= 0),
    cited_post_id uuid not null references source_post(post_id) on delete cascade,
    primary key (global_ask_session_id, turn_ordinal, citation_ordinal),
    foreign key (global_ask_session_id, turn_ordinal)
        references global_ask_turn(global_ask_session_id, turn_ordinal)
        on delete cascade
);
create table if not exists global_ask_turn_source (
    global_ask_session_id uuid not null,
    turn_ordinal integer not null,
    source_ordinal integer not null check (source_ordinal >= 0),
    source_post_id uuid not null references source_post(post_id) on delete cascade,
    primary key (global_ask_session_id, turn_ordinal, source_ordinal),
    unique (global_ask_session_id, turn_ordinal, source_post_id),
    foreign key (global_ask_session_id, turn_ordinal)
        references global_ask_turn(global_ask_session_id, turn_ordinal)
        on delete cascade
);

create table if not exists global_ask_turn_evidence (
    global_ask_session_id uuid not null,
    turn_ordinal integer not null,
    cited_post_id uuid not null references source_post(post_id) on delete cascade,
    fact_ordinal integer not null check (fact_ordinal >= 0),
    fact_kind text not null,
    fact_text text not null,
    primary key (global_ask_session_id, turn_ordinal, cited_post_id, fact_ordinal),
    foreign key (global_ask_session_id, turn_ordinal)
        references global_ask_turn(global_ask_session_id, turn_ordinal)
        on delete cascade
);

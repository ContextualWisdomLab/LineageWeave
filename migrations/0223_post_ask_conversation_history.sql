-- ADR 0235: persist account-owned Ask conversations on each visible post.
-- Third normal form: session identity, turn text, and citation/source
-- relations are separate tables. Index leads with user_account_id so a
-- frequently asked post cannot become a single hot partition key.

create table if not exists post_ask_session (
    post_ask_session_id uuid primary key,
    post_id uuid not null references source_post(post_id) on delete cascade,
    user_account_id uuid not null references user_account(user_account_id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists post_ask_session_account_post_idx
    on post_ask_session (user_account_id, post_id, updated_at desc);

create table if not exists post_ask_turn (
    post_ask_session_id uuid not null
        references post_ask_session(post_ask_session_id) on delete cascade,
    turn_ordinal integer not null check (turn_ordinal > 0),
    question_text text not null,
    answer_text text not null,
    created_at timestamptz not null default now(),
    primary key (post_ask_session_id, turn_ordinal)
);

create table if not exists post_ask_turn_citation (
    post_ask_session_id uuid not null,
    turn_ordinal integer not null,
    citation_ordinal integer not null check (citation_ordinal >= 0),
    cited_post_id uuid not null references source_post(post_id) on delete cascade,
    primary key (post_ask_session_id, turn_ordinal, citation_ordinal),
    foreign key (post_ask_session_id, turn_ordinal)
        references post_ask_turn(post_ask_session_id, turn_ordinal)
        on delete cascade
);

create table if not exists post_ask_turn_source (
    post_ask_session_id uuid not null,
    turn_ordinal integer not null,
    source_ordinal integer not null check (source_ordinal >= 0),
    source_post_id uuid not null references source_post(post_id) on delete cascade,
    primary key (post_ask_session_id, turn_ordinal, source_ordinal),
    unique (post_ask_session_id, turn_ordinal, source_post_id),
    foreign key (post_ask_session_id, turn_ordinal)
        references post_ask_turn(post_ask_session_id, turn_ordinal)
        on delete cascade
);

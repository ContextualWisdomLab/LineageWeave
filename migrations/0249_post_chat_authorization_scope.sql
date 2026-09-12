-- Persist immutable authorization evidence for derived Post Chat answers.
-- ADR 0373: legacy rows without a receipt intentionally remain non-replayable.

create table if not exists post_chat_authorization_receipt (
    post_id uuid not null,
    question_norm text not null,
    process_scope_limited boolean not null,
    captured_at timestamptz not null default now(),
    primary key (post_id, question_norm),
    foreign key (post_id, question_norm)
        references post_chat_result (post_id, question_norm) on delete cascade
);

create table if not exists post_chat_corporate_entity_scope (
    post_id uuid not null,
    question_norm text not null,
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    primary key (post_id, question_norm, corporate_entity_id),
    foreign key (post_id, question_norm)
        references post_chat_authorization_receipt (post_id, question_norm) on delete cascade
);

create table if not exists post_chat_process_unit_scope (
    post_id uuid not null,
    question_norm text not null,
    process_unit_id uuid not null references process_unit (process_unit_id),
    primary key (post_id, question_norm, process_unit_id),
    foreign key (post_id, question_norm)
        references post_chat_authorization_receipt (post_id, question_norm) on delete cascade
);

create table if not exists post_chat_source (
    post_id uuid not null,
    question_norm text not null,
    source_ordinal integer not null check (source_ordinal >= 0),
    source_post_id uuid not null references source_post (post_id) on delete cascade,
    primary key (post_id, question_norm, source_ordinal),
    unique (post_id, question_norm, source_post_id),
    foreign key (post_id, question_norm)
        references post_chat_authorization_receipt (post_id, question_norm) on delete cascade
);

-- Derived text is no longer replay-safe once any source that influenced it is
-- deleted. Run before the source_post FK cascade so the captured source rows
-- are still available to locate and atomically delete their parent answers.
create or replace function invalidate_post_chat_replay_on_source_post_delete()
returns trigger
language plpgsql
as $$
begin
    delete from post_chat_result result
    using post_chat_source captured_source
    where captured_source.source_post_id = old.post_id
      and result.post_id = captured_source.post_id
      and result.question_norm = captured_source.question_norm;
    return old;
end;
$$;

drop trigger if exists invalidate_post_chat_replay_on_source_delete on source_post;
create trigger invalidate_post_chat_replay_on_source_delete
before delete on source_post
for each row
execute function invalidate_post_chat_replay_on_source_post_delete();

comment on table post_chat_authorization_receipt is
    'Presence distinguishes a scoped replay receipt from a legacy unscoped answer; process_scope_limited preserves authenticated unrestricted empty-set semantics.';
comment on table post_chat_corporate_entity_scope is
    'Corporate-entity authorization scope captured when a persisted Post Chat answer is generated.';
comment on table post_chat_process_unit_scope is
    'Restricted process-unit authorization scope captured when a persisted Post Chat answer is generated.';
comment on table post_chat_source is
    'Ordered source posts that could influence persisted Post Chat derived text and must all be reauthorized before replay.';
comment on function invalidate_post_chat_replay_on_source_post_delete() is
    'Invalidates persisted derived answers before a contributing source is deleted so stale source-derived text cannot be replayed.';

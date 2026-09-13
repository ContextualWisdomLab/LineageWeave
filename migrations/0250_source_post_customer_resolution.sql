begin;

create table source_post_customer_resolution (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_customer_code text not null,
    resolved_corporate_entity_id uuid not null references corporate_entity(corporate_entity_id),
    resolved_entity_name text not null,
    verification_status_code text not null,
    verification_evidence_url text,
    resolved_at timestamptz not null default now(),
    constraint source_post_customer_resolution_hint_nonblank
        check (btrim(source_customer_code) <> ''),
    constraint source_post_customer_resolution_name_nonblank
        check (btrim(resolved_entity_name) <> '')
);

create index source_post_customer_resolution_entity_idx
    on source_post_customer_resolution (resolved_corporate_entity_id, post_id);

comment on table source_post_customer_resolution is
    'Corroborated Customer Master identity for a source post. source_post corporate/process columns remain authorization ownership.';
comment on column source_post_customer_resolution.source_customer_code is
    'Raw customer hint copied at corroboration time so retries and later source edits remain auditable.';
comment on column source_post_customer_resolution.resolved_corporate_entity_id is
    'Catalog identity only; never grants access to or changes source_post tenant ownership.';

commit;

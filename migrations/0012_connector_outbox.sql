-- ADR 0014: transactional connector outbox before Valkey publish.
-- TEPP / orchestrator submits persist here first; a later flush XADDs
-- onto outbox:{connector_code}. No invented theta is stored.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('connector_kind', 'connector_tepp', 'TEPP', 0),
    ('connector_kind', 'connector_orchestrator', 'contextual-orchestrator', 1),
    ('outbox_delivery_status', 'outbox_pending', 'Pending', 0),
    ('outbox_delivery_status', 'outbox_published', 'Published', 1),
    ('outbox_delivery_status', 'outbox_failed', 'Failed', 2)
on conflict (lookup_code) do nothing;

create table if not exists connector_outbox_event (
    outbox_event_id uuid primary key default uuid_generate_v4(),
    connector_code text not null
        references common_lookup_value (lookup_code),
    delivery_status_code text not null
        references common_lookup_value (lookup_code),
    idempotency_key text not null,
    payload_sha256 text not null,
    payload_json jsonb not null,
    stream_entry_id text,
    failure_code text,
    created_at timestamptz not null default now(),
    published_at timestamptz,
    unique (connector_code, idempotency_key)
);

create index if not exists connector_outbox_event_pending_idx
    on connector_outbox_event (delivery_status_code, created_at)
    where delivery_status_code = 'outbox_pending';

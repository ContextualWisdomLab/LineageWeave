-- ADR 0026: transactional activity outbox. Persist the ticket event in
-- PostgreSQL first, then XADD onto Valkey. CREATE IF NOT EXISTS so a
-- volume that already ran 0001 still upgrades. Lookup codes are unique
-- across categories (see 0001). Never store a fused score or a theta.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('activity_event_type', 'ticket_created', 'Ticket created', 0),
    ('activity_event_type', 'ticket_status_changed', 'Ticket status changed', 1),
    ('activity_event_type', 'commitment_derived', 'Commitment derived', 2),
    ('outbox_delivery_status', 'outbox_pending', 'Pending', 0),
    ('outbox_delivery_status', 'outbox_delivered', 'Delivered', 1),
    ('outbox_delivery_status', 'outbox_failed', 'Failed', 2)
on conflict (lookup_code) do nothing;

create table if not exists activity_outbox_event (
    outbox_event_id uuid primary key default uuid_generate_v4(),
    post_id uuid not null references source_post (post_id),
    issue_ticket_id uuid references issue_ticket (issue_ticket_id),
    event_type_code text not null references common_lookup_value (lookup_code),
    actor_account_id uuid not null references user_account (user_account_id),
    event_summary text not null,
    delivery_status_code text not null references common_lookup_value (lookup_code),
    valkey_entry_id text,
    requested_at timestamptz not null default now(),
    delivered_at timestamptz,
    unique (post_id, event_type_code, event_summary),
    check (
        (delivery_status_code = 'outbox_delivered' and valkey_entry_id is not null and delivered_at is not null)
        or (delivery_status_code <> 'outbox_delivered' and valkey_entry_id is null)
    )
);

create index if not exists activity_outbox_event_post_idx
    on activity_outbox_event (post_id);
create index if not exists activity_outbox_event_status_idx
    on activity_outbox_event (delivery_status_code, requested_at desc);

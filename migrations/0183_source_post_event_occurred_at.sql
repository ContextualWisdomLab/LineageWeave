-- ADR 0183: persist the source-system event instant separately from
-- record ingestion time. Nullable so bulk imports without an event
-- clock keep the created_at fallback instead of inventing a date.

alter table source_post
    add column if not exists event_occurred_at timestamptz;

comment on column source_post.event_occurred_at is
    'Source-system event instant for Global Ask relative-time filters. '
    'Null means Ask falls back to created_at (record ingestion) and names that axis.';

-- Migration 0257 / ADR 0098: stop the bounded backfill scan in source order.
create index if not exists source_post_content_backfill_candidate_idx
    on source_post (
        coalesce(event_occurred_at, created_at),
        created_at,
        post_id
    )
    where nullif(btrim(source_draft_code), '') is null
      and nullif(btrim(source_deleted_flag), '') is null;

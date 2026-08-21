begin;

-- Preserve caller-mapped source lifecycle fields without inferring their
-- meaning or collapsing stage, detail state, draft, and deletion signals.
alter table source_post add column if not exists source_stage_code text;
alter table source_post add column if not exists source_detail_state_code text;
alter table source_post add column if not exists source_draft_code text;
alter table source_post add column if not exists source_deleted_flag text;

comment on column source_post.source_stage_code is
    'Raw source stage/status code; nullable because the source query may omit it.';
comment on column source_post.source_detail_state_code is
    'Raw source detail-state code; never treated as a product publication label.';
comment on column source_post.source_draft_code is
    'Raw source draft/property marker; null is preserved and is not interpreted.';
comment on column source_post.source_deleted_flag is
    'Raw source deletion marker; retained separately from stage and detail state.';

commit;

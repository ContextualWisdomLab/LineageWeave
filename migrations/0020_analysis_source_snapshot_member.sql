-- Create-time cutoff membership for an analysis source snapshot (ADR 0019).
--
-- The snapshot digest already hashes authorized post ids. This relation
-- stores those ids so start reconstructs the same bag, not a later
-- backfill that shares the cutoff clock. No post body is stored.

create table if not exists analysis_source_snapshot_member (
    analysis_source_snapshot_id uuid not null
        references analysis_source_snapshot (analysis_source_snapshot_id),
    source_post_id uuid not null
        references source_post (post_id),
    primary key (analysis_source_snapshot_id, source_post_id)
);

comment on table analysis_source_snapshot_member is
    'Authorized post ids frozen at snapshot capture; start reconstructs '
    'these rows and never a later backfill.';

create or replace function reject_analysis_source_snapshot_member_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_source_snapshot_member_is_immutable';
end
$$;

comment on function reject_analysis_source_snapshot_member_update() is
    'Rejects mutation of frozen snapshot membership.';

drop trigger if exists analysis_source_snapshot_member_update_reject
    on analysis_source_snapshot_member;
create trigger analysis_source_snapshot_member_update_reject
before update or delete on analysis_source_snapshot_member
for each row execute function reject_analysis_source_snapshot_member_update();

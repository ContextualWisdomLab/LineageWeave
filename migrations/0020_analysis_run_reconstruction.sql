-- Run-scoped lineage reconstruction result (ADR 0020).
--
-- A Pending analysis run may later persist the ThreadWeave parent choices
-- for its cutoff bag. Edges belong to the run, not the live Event Lineage
-- panel. No post body, DSN, or fabricated measurement is stored.

create table if not exists analysis_run_reconstruction (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    result_sha256 text not null,
    edge_count integer not null,
    reconstructed_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    constraint analysis_run_reconstruction_digest_check
        check (result_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_reconstruction_edge_count_check
        check (edge_count >= 0),
    constraint analysis_run_reconstruction_time_check
        check (reconstructed_at <= recorded_at)
);

comment on table analysis_run_reconstruction is
    'One immutable reconstruction digest per analysis run; never a post body '
    'or a fabricated psychometric score.';

create table if not exists analysis_run_lineage_edge (
    analysis_run_id uuid not null
        references analysis_run_reconstruction (analysis_run_id),
    child_post_id uuid not null
        references source_post (post_id),
    parent_post_id uuid not null
        references source_post (post_id),
    fused_score double precision not null,
    reconstructed_at timestamptz not null,
    primary key (analysis_run_id, child_post_id),
    constraint analysis_run_lineage_edge_distinct_check
        check (child_post_id <> parent_post_id),
    constraint analysis_run_lineage_edge_score_check
        check (fused_score >= 0 and fused_score <= 1)
);

comment on table analysis_run_lineage_edge is
    'One reconstructed parent choice per child post inside one analysis run.';

create or replace function reject_analysis_run_reconstruction_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_reconstruction_is_immutable';
end
$$;

comment on function reject_analysis_run_reconstruction_update() is
    'Rejects mutation of a persisted reconstruction digest.';

drop trigger if exists analysis_run_reconstruction_update_reject
    on analysis_run_reconstruction;
create trigger analysis_run_reconstruction_update_reject
before update or delete on analysis_run_reconstruction
for each row execute function reject_analysis_run_reconstruction_update();

create or replace function reject_analysis_run_lineage_edge_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_lineage_edge_is_immutable';
end
$$;

comment on function reject_analysis_run_lineage_edge_update() is
    'Rejects mutation of a persisted run-scoped lineage edge.';

drop trigger if exists analysis_run_lineage_edge_update_reject
    on analysis_run_lineage_edge;
create trigger analysis_run_lineage_edge_update_reject
before update or delete on analysis_run_lineage_edge
for each row execute function reject_analysis_run_lineage_edge_update();

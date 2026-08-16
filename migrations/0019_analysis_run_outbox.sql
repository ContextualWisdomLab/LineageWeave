-- Milestone 2 lineage delivery: PostgreSQL outbox plus run-scoped edges.
--
-- ADR 0013 follow-up 3 / ADR 0018. POST /api/analysis-runs stays a Pending
-- write. This migration records one delivery row per run and the parent→child
-- edges that reconstruction produced for that run. It does not store post
-- bodies, DSNs, provider payloads, or a TEPP theta. Global post_lineage_edge
-- remains the live navigation projection and is not replaced here.

begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('analysis_delivery_kind', 'analysis_delivery_lineage', 'Lineage reconstruction delivery', 0),
    ('analysis_delivery_status', 'analysis_delivery_queued', 'Queued', 0),
    ('analysis_delivery_status', 'analysis_delivery_leased', 'Leased', 1),
    ('analysis_delivery_status', 'analysis_delivery_completed', 'Completed', 2),
    ('analysis_delivery_status', 'analysis_delivery_failed', 'Failed', 3)
on conflict (lookup_code) do nothing;

do $$
declare
    lookup_mismatch_count integer;
begin
    select count(*)
      into lookup_mismatch_count
      from common_lookup_value as actual
      join (values
          ('analysis_delivery_lineage', 'analysis_delivery_kind'),
          ('analysis_delivery_queued', 'analysis_delivery_status'),
          ('analysis_delivery_leased', 'analysis_delivery_status'),
          ('analysis_delivery_completed', 'analysis_delivery_status'),
          ('analysis_delivery_failed', 'analysis_delivery_status')
      ) as expected(lookup_code, lookup_category)
        on expected.lookup_code = actual.lookup_code
     where actual.lookup_category <> expected.lookup_category;

    if lookup_mismatch_count <> 0 then
        raise exception 'analysis_run_outbox_lookup_conflict';
    end if;
end
$$;

create table if not exists analysis_run_outbox (
    analysis_run_id uuid primary key
        references analysis_run (analysis_run_id),
    delivery_kind_code text not null
        references common_lookup_value (lookup_code),
    delivery_status_code text not null
        references common_lookup_value (lookup_code),
    lease_token text,
    leased_until timestamptz,
    attempt_count integer not null default 0,
    last_attempt_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    constraint analysis_run_outbox_kind_check
        check (delivery_kind_code = 'analysis_delivery_lineage'),
    constraint analysis_run_outbox_status_check
        check (delivery_status_code in (
            'analysis_delivery_queued',
            'analysis_delivery_leased',
            'analysis_delivery_completed',
            'analysis_delivery_failed'
        )),
    constraint analysis_run_outbox_attempt_check
        check (attempt_count >= 0),
    constraint analysis_run_outbox_lease_shape_check
        check (
            (delivery_status_code <> 'analysis_delivery_leased'
             and lease_token is null
             and leased_until is null)
            or
            (delivery_status_code = 'analysis_delivery_leased'
             and lease_token is not null
             and leased_until is not null)
        ),
    constraint analysis_run_outbox_completed_shape_check
        check (
            (delivery_status_code <> 'analysis_delivery_completed'
             and completed_at is null)
            or
            (delivery_status_code = 'analysis_delivery_completed'
             and completed_at is not null)
        )
);

comment on table analysis_run_outbox is
    'One lineage delivery lease per analysis run; Valkey may signal, PostgreSQL remains source of truth.';

comment on column analysis_run_outbox.analysis_run_id is
    'The Pending run this delivery will advance; 1:1 so a replay cannot enqueue a second worker.';

comment on column analysis_run_outbox.delivery_kind_code is
    'Lineage only in this slice. TEPP execution stays a later adapter.';

create table if not exists analysis_run_lineage_edge (
    analysis_run_id uuid not null
        references analysis_run (analysis_run_id),
    parent_post_id uuid not null
        references source_post (post_id),
    child_post_id uuid not null
        references source_post (post_id),
    fused_score double precision not null,
    recorded_at timestamptz not null default now(),
    primary key (analysis_run_id, parent_post_id, child_post_id),
    constraint analysis_run_lineage_edge_distinct_check
        check (parent_post_id <> child_post_id),
    constraint analysis_run_lineage_edge_score_check
        check (fused_score >= 0 and fused_score <= 1)
);

comment on table analysis_run_lineage_edge is
    'Run-scoped reconstruction edges for one cutoff bag. Does not replace live post_lineage_edge.';

comment on column analysis_run_lineage_edge.fused_score is
    'RankWeave fused parent choice in [0, 1]; never a TEPP theta.';

create or replace function reject_analysis_run_lineage_edge_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_lineage_edge_immutable';
end
$$;

comment on function reject_analysis_run_lineage_edge_mutation() is
    'Edges are insert-only. A failed transaction rolls back partial inserts.';

drop trigger if exists analysis_run_lineage_edge_update_guard
    on analysis_run_lineage_edge;
create trigger analysis_run_lineage_edge_update_guard
before update or delete on analysis_run_lineage_edge
for each row execute function reject_analysis_run_lineage_edge_mutation();

commit;

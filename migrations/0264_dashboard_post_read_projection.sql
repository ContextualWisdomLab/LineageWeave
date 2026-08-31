-- ADR 0272: maintained narrow projection for exact, authorized Dashboard reads.
create table if not exists dashboard_post_read_projection (
    source_post_id uuid primary key references source_post(post_id) on delete cascade,
    corporate_entity_id uuid not null,
    process_unit_id uuid,
    visibility_code text not null,
    occurred_date date not null,
    occurred_at timestamptz,
    source_project_code text,
    source_project_name text,
    active_source boolean not null,
    source_context_present boolean not null,
    case_analysis_present boolean not null,
    ingestion_failed boolean not null
);

alter table dashboard_post_read_projection
    add column if not exists occurred_at timestamptz;
alter table dashboard_post_read_projection
    add column if not exists source_project_name text;
alter table dashboard_post_read_projection
    add column if not exists source_project_code text;

create or replace function refresh_dashboard_post_read_projection(target_post_id uuid)
returns void
language sql
as $$
    insert into dashboard_post_read_projection (
        source_post_id, corporate_entity_id, process_unit_id, visibility_code,
        occurred_date, occurred_at, source_project_code, source_project_name,
        active_source, source_context_present,
        case_analysis_present, ingestion_failed
    )
    select post.post_id, post.corporate_entity_id, post.process_unit_id,
           post.visibility_code,
           (coalesce(post.event_occurred_at, post.created_at)
               at time zone 'Asia/Seoul')::date,
           coalesce(post.event_occurred_at, post.created_at),
           post.source_project_code,
           post.source_project_name,
           (post.source_draft_code is null or btrim(post.source_draft_code) = '')
               and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = ''),
           nullif(btrim(post.source_author_code), '') is not null
               or nullif(btrim(post.source_author_name), '') is not null
               or nullif(btrim(post.source_company_code), '') is not null
               or nullif(btrim(post.source_company_name), '') is not null
               or nullif(btrim(post.source_process_unit_code), '') is not null
               or nullif(btrim(post.source_process_unit_name), '') is not null
               or nullif(btrim(post.source_sales_pool_code), '') is not null
               or nullif(btrim(post.source_sales_pool_name), '') is not null
               or nullif(btrim(post.source_customer_code), '') is not null
               or nullif(btrim(post.source_customer_name), '') is not null
               or nullif(btrim(post.source_project_code), '') is not null
               or nullif(btrim(post.source_project_name), '') is not null,
           exists (select 1 from operations_case_analysis analysis
                    where analysis.post_id = post.post_id),
           exists (select 1 from post_content_ingestion_job job
                    where job.post_id = post.post_id
                      and job.status_code = 'post_content_ingestion_failed')
      from source_post post
     where post.post_id = target_post_id
    on conflict (source_post_id) do update set
        corporate_entity_id = excluded.corporate_entity_id,
        process_unit_id = excluded.process_unit_id,
        visibility_code = excluded.visibility_code,
        occurred_date = excluded.occurred_date,
        occurred_at = excluded.occurred_at,
        source_project_code = excluded.source_project_code,
        source_project_name = excluded.source_project_name,
        active_source = excluded.active_source,
        source_context_present = excluded.source_context_present,
        case_analysis_present = excluded.case_analysis_present,
        ingestion_failed = excluded.ingestion_failed;
$$;

create or replace function refresh_dashboard_post_read_projection_trigger()
returns trigger
language plpgsql
as $$
begin
    perform refresh_dashboard_post_read_projection(coalesce(new.post_id, old.post_id));
    return null;
end;
$$;

do $migration$
begin
    if not exists (select 1 from pg_trigger where tgrelid = 'source_post'::regclass
                   and tgname = 'dashboard_source_post_read_projection_trigger'
                   and not tgisinternal) then
        create trigger dashboard_source_post_read_projection_trigger
        after insert or update on source_post
        for each row execute function refresh_dashboard_post_read_projection_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'operations_case_analysis'::regclass
                   and tgname = 'dashboard_case_analysis_read_projection_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_analysis_read_projection_trigger
        after insert or update or delete on operations_case_analysis
        for each row execute function refresh_dashboard_post_read_projection_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'post_content_ingestion_job'::regclass
                   and tgname = 'dashboard_ingestion_job_read_projection_trigger'
                   and not tgisinternal) then
        create trigger dashboard_ingestion_job_read_projection_trigger
        after insert or update or delete on post_content_ingestion_job
        for each row execute function refresh_dashboard_post_read_projection_trigger();
    end if;
end
$migration$;

insert into dashboard_post_read_projection (
    source_post_id, corporate_entity_id, process_unit_id, visibility_code,
    occurred_date, occurred_at, source_project_code, source_project_name,
    active_source, source_context_present,
    case_analysis_present, ingestion_failed
)
select post.post_id, post.corporate_entity_id, post.process_unit_id,
       post.visibility_code,
       (coalesce(post.event_occurred_at, post.created_at)
           at time zone 'Asia/Seoul')::date,
       coalesce(post.event_occurred_at, post.created_at),
       post.source_project_code,
       post.source_project_name,
       (post.source_draft_code is null or btrim(post.source_draft_code) = '')
           and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = ''),
       nullif(btrim(post.source_author_code), '') is not null
           or nullif(btrim(post.source_author_name), '') is not null
           or nullif(btrim(post.source_company_code), '') is not null
           or nullif(btrim(post.source_company_name), '') is not null
           or nullif(btrim(post.source_process_unit_code), '') is not null
           or nullif(btrim(post.source_process_unit_name), '') is not null
           or nullif(btrim(post.source_sales_pool_code), '') is not null
           or nullif(btrim(post.source_sales_pool_name), '') is not null
           or nullif(btrim(post.source_customer_code), '') is not null
           or nullif(btrim(post.source_customer_name), '') is not null
           or nullif(btrim(post.source_project_code), '') is not null
           or nullif(btrim(post.source_project_name), '') is not null,
       exists (select 1 from operations_case_analysis analysis
               where analysis.post_id = post.post_id),
       exists (select 1 from post_content_ingestion_job job
               where job.post_id = post.post_id
                 and job.status_code = 'post_content_ingestion_failed')
  from source_post post
on conflict (source_post_id) do nothing;

create index if not exists dashboard_post_public_period_idx
    on dashboard_post_read_projection (occurred_date, source_post_id)
    where active_source and visibility_code = 'public';

create index if not exists dashboard_post_public_case_page_idx
    on dashboard_post_read_projection (occurred_at desc, source_post_id desc)
    include (source_project_name)
    where active_source and visibility_code = 'public';

create index if not exists dashboard_post_public_summary_idx
    on dashboard_post_read_projection (occurred_date, source_post_id)
    include (case_analysis_present, ingestion_failed, source_context_present)
    where active_source and visibility_code = 'public';

create index if not exists dashboard_post_entity_period_idx
    on dashboard_post_read_projection (
        corporate_entity_id, process_unit_id, occurred_date, source_post_id
    )
    where active_source;

create index if not exists dashboard_post_context_access_idx
    on dashboard_post_read_projection (
        source_context_present, visibility_code, corporate_entity_id, process_unit_id
    )
    where active_source;

create table if not exists dashboard_post_daily_summary (
    occurred_date date not null,
    visibility_code text not null,
    corporate_entity_id uuid not null,
    process_unit_id uuid,
    source_context_present boolean not null,
    total_post_count bigint not null,
    pending_analysis_count bigint not null,
    failed_analysis_count bigint not null
);

create unique index if not exists dashboard_post_daily_summary_identity_idx
    on dashboard_post_daily_summary (
        occurred_date, visibility_code, corporate_entity_id,
        process_unit_id, source_context_present
    ) nulls not distinct;

create or replace function maintain_dashboard_post_daily_summary()
returns trigger
language plpgsql
as $$
begin
    if tg_op in ('UPDATE', 'DELETE') and old.active_source then
        insert into dashboard_post_daily_summary (
            occurred_date, visibility_code, corporate_entity_id, process_unit_id,
            source_context_present, total_post_count,
            pending_analysis_count, failed_analysis_count
        ) values (
            old.occurred_date, old.visibility_code, old.corporate_entity_id,
            old.process_unit_id, old.source_context_present, -1,
            -((not old.case_analysis_present and not old.ingestion_failed)::int),
            -(old.ingestion_failed::int)
        )
        on conflict (occurred_date, visibility_code, corporate_entity_id,
                     process_unit_id, source_context_present)
        do update set
            total_post_count = dashboard_post_daily_summary.total_post_count - 1,
            pending_analysis_count = dashboard_post_daily_summary.pending_analysis_count
                - ((not old.case_analysis_present and not old.ingestion_failed)::int),
            failed_analysis_count = dashboard_post_daily_summary.failed_analysis_count
                - (old.ingestion_failed::int);
    end if;
    if tg_op in ('INSERT', 'UPDATE') and new.active_source then
        insert into dashboard_post_daily_summary (
            occurred_date, visibility_code, corporate_entity_id, process_unit_id,
            source_context_present, total_post_count,
            pending_analysis_count, failed_analysis_count
        ) values (
            new.occurred_date, new.visibility_code, new.corporate_entity_id,
            new.process_unit_id, new.source_context_present, 1,
            (not new.case_analysis_present and not new.ingestion_failed)::int,
            new.ingestion_failed::int
        )
        on conflict (occurred_date, visibility_code, corporate_entity_id,
                     process_unit_id, source_context_present)
        do update set
            total_post_count = dashboard_post_daily_summary.total_post_count + 1,
            pending_analysis_count = dashboard_post_daily_summary.pending_analysis_count
                + ((not new.case_analysis_present and not new.ingestion_failed)::int),
            failed_analysis_count = dashboard_post_daily_summary.failed_analysis_count
                + (new.ingestion_failed::int);
    end if;
    delete from dashboard_post_daily_summary
     where total_post_count = 0;
    return null;
end;
$$;

do $migration$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'dashboard_post_read_projection'::regclass
           and tgname = 'dashboard_post_daily_summary_trigger'
           and not tgisinternal
    ) then
        create trigger dashboard_post_daily_summary_trigger
        after insert or update or delete on dashboard_post_read_projection
        for each row execute function maintain_dashboard_post_daily_summary();
    end if;
end
$migration$;

insert into dashboard_post_daily_summary (
    occurred_date, visibility_code, corporate_entity_id, process_unit_id,
    source_context_present, total_post_count,
    pending_analysis_count, failed_analysis_count
)
select occurred_date, visibility_code, corporate_entity_id, process_unit_id,
       source_context_present, count(*),
       count(*) filter (where not case_analysis_present and not ingestion_failed),
       count(*) filter (where ingestion_failed)
  from dashboard_post_read_projection
 where active_source
 group by occurred_date, visibility_code, corporate_entity_id, process_unit_id,
          source_context_present
on conflict do nothing;

-- One row per persisted case keeps exact Event/Post and lifecycle totals out of
-- the interactive join path. Evidence ids remain explicit so caller ABAC can
-- reject the entire row when any contributing source is not visible.
create table if not exists dashboard_case_rollup_read_projection (
    source_post_id uuid not null references source_post(post_id) on delete cascade,
    case_kind_code text not null,
    classification_evidence_post_id uuid not null references source_post(post_id),
    summary_text text,
    evidence_text text,
    occurred_at timestamptz,
    project_name text,
    project_names text[] not null default '{}',
    claim_start_missing boolean not null,
    rebid_start_missing boolean not null,
    handover_start_missing boolean not null,
    primary key (source_post_id, case_kind_code)
);

alter table dashboard_case_rollup_read_projection
    add column if not exists summary_text text;
alter table dashboard_case_rollup_read_projection
    add column if not exists evidence_text text;
alter table dashboard_case_rollup_read_projection
    add column if not exists occurred_at timestamptz;
alter table dashboard_case_rollup_read_projection
    add column if not exists project_name text;
alter table dashboard_case_rollup_read_projection
    add column if not exists project_names text[] not null default '{}';

create table if not exists dashboard_case_milestone_read_projection (
    source_post_id uuid not null references source_post(post_id) on delete cascade,
    case_kind_code text not null,
    evidence_post_id uuid not null references source_post(post_id),
    event_count bigint not null,
    claim_started boolean not null,
    claim_ended boolean not null,
    rebid_started boolean not null,
    rebid_ended boolean not null,
    handover_started boolean not null,
    handover_ended boolean not null,
    primary key (source_post_id, case_kind_code, evidence_post_id)
);

create table if not exists dashboard_case_contributor_read_projection (
    source_post_id uuid not null references source_post(post_id) on delete cascade,
    case_kind_code text not null,
    evidence_post_id uuid not null references source_post(post_id),
    primary key (source_post_id, case_kind_code, evidence_post_id)
);

create or replace function refresh_dashboard_case_rollup_read_projection(
    target_post_id uuid,
    target_case_kind_code text
)
returns void
language plpgsql
as $$
begin
    delete from dashboard_case_contributor_read_projection projection
     where projection.source_post_id = target_post_id
       and projection.case_kind_code = target_case_kind_code;
    delete from dashboard_case_milestone_read_projection projection
     where projection.source_post_id = target_post_id
       and projection.case_kind_code = target_case_kind_code;
    delete from dashboard_case_rollup_read_projection projection
     where projection.source_post_id = target_post_id
       and projection.case_kind_code = target_case_kind_code;

    insert into dashboard_case_rollup_read_projection (
        source_post_id, case_kind_code, classification_evidence_post_id,
        summary_text, evidence_text, occurred_at, project_name, project_names,
        claim_start_missing,
        rebid_start_missing, handover_start_missing
    )
    select classification.post_id, classification.case_kind_code,
           classification.evidence_post_id,
           classification.summary_text, classification.evidence_text,
           post.occurred_at,
           coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name,
                    nullif(btrim(post.source_project_code), '')),
           coalesce(project.project_names, array[]::text[]),
           exists (select 1 from operations_case_missing_milestone missing
                    where missing.post_id = classification.post_id
                      and missing.case_kind_code = classification.case_kind_code
                      and missing.milestone_type_code = 'claim_received'),
           exists (select 1 from operations_case_missing_milestone missing
                    where missing.post_id = classification.post_id
                      and missing.case_kind_code = classification.case_kind_code
                      and missing.milestone_type_code = 'rebid_response_requested'),
           exists (select 1 from operations_case_missing_milestone missing
                    where missing.post_id = classification.post_id
                      and missing.case_kind_code = classification.case_kind_code
                      and missing.milestone_type_code = 'handover_started')
      from operations_case_classification classification
      join dashboard_post_read_projection post
        on post.source_post_id = classification.post_id
      left join lateral (
          select array_agg(names.project_name order by names.project_name) as project_names,
                 (select nullif(btrim(primary_mention.project_name), '')
                    from post_project_mention primary_mention
                   where primary_mention.post_id = classification.post_id
                     and nullif(btrim(primary_mention.project_name), '') is not null
                   order by primary_mention.confidence desc,
                            primary_mention.project_name
                   limit 1) as primary_project_name
            from (
                select coalesce(nullif(btrim(post.source_project_name), ''),
                                nullif(btrim(post.source_project_code), '')) as project_name
                union
                select nullif(btrim(mention.project_name), '')
                  from post_project_mention mention
                 where mention.post_id = classification.post_id
            ) names
           where names.project_name is not null
      ) project on true
     where classification.post_id = target_post_id
       and classification.case_kind_code = target_case_kind_code;

    insert into dashboard_case_contributor_read_projection (
        source_post_id, case_kind_code, evidence_post_id
    )
    select contributor.post_id, contributor.case_kind_code,
           contributor.evidence_post_id
      from (
          select post_id, case_kind_code, evidence_post_id
            from operations_case_classification
          union
          select post_id, case_kind_code, evidence_post_id
            from operations_case_milestone
          union
          select post_id, case_kind_code, evidence_post_id
            from operations_case_fact
          union
          select post_id, case_kind_code, evidence_post_id
            from product_operations_fact_relation
      ) contributor
     where contributor.post_id = target_post_id
       and contributor.case_kind_code = target_case_kind_code;

    insert into dashboard_case_milestone_read_projection (
        source_post_id, case_kind_code, evidence_post_id, event_count,
        claim_started, claim_ended, rebid_started, rebid_ended,
        handover_started, handover_ended
    )
    select milestone.post_id, milestone.case_kind_code,
           milestone.evidence_post_id, count(*),
           bool_or(milestone.milestone_type_code = 'claim_received'),
           bool_or(milestone.milestone_type_code = 'cause_confirmed'),
           bool_or(milestone.milestone_type_code = 'rebid_response_requested'),
           bool_or(milestone.milestone_type_code = 'rebid_decision_recorded'),
           bool_or(milestone.milestone_type_code = 'handover_started'),
           bool_or(milestone.milestone_type_code = 'handover_accepted')
      from operations_case_milestone milestone
     where milestone.post_id = target_post_id
       and milestone.case_kind_code = target_case_kind_code
     group by milestone.post_id, milestone.case_kind_code,
              milestone.evidence_post_id;
end;
$$;

create or replace function refresh_dashboard_case_rollup_read_projection_trigger()
returns trigger
language plpgsql
as $$
begin
    if tg_op in ('UPDATE', 'DELETE') then
        perform refresh_dashboard_case_rollup_read_projection(
            old.post_id, old.case_kind_code
        );
    end if;
    if tg_op in ('INSERT', 'UPDATE')
       and (tg_op = 'INSERT'
            or (new.post_id, new.case_kind_code)
               is distinct from (old.post_id, old.case_kind_code)) then
        perform refresh_dashboard_case_rollup_read_projection(
            new.post_id, new.case_kind_code
        );
    end if;
    return null;
end;
$$;

create or replace function refresh_dashboard_case_rollup_from_project_trigger()
returns trigger
language plpgsql
as $$
declare
    target_post_id uuid := coalesce(new.post_id, old.post_id);
    case_row record;
begin
    for case_row in
        select classification.case_kind_code
          from operations_case_classification classification
         where classification.post_id = target_post_id
    loop
        perform refresh_dashboard_case_rollup_read_projection(
            target_post_id, case_row.case_kind_code
        );
    end loop;
    return null;
end;
$$;
create or replace function refresh_dashboard_case_rollup_from_post_trigger()
returns trigger
language plpgsql
as $$
declare
    case_row record;
begin
    for case_row in
        select classification.case_kind_code
          from operations_case_classification classification
         where classification.post_id = coalesce(new.source_post_id, old.source_post_id)
    loop
        perform refresh_dashboard_case_rollup_read_projection(
            coalesce(new.source_post_id, old.source_post_id),
            case_row.case_kind_code
        );
    end loop;
    return null;
end;
$$;

do $migration$
begin
    if not exists (select 1 from pg_trigger where tgrelid = 'operations_case_classification'::regclass
                   and tgname = 'dashboard_case_rollup_classification_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_classification_trigger
        after insert or update or delete on operations_case_classification
        for each row execute function refresh_dashboard_case_rollup_read_projection_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'operations_case_milestone'::regclass
                   and tgname = 'dashboard_case_rollup_milestone_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_milestone_trigger
        after insert or update or delete on operations_case_milestone
        for each row execute function refresh_dashboard_case_rollup_read_projection_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'operations_case_fact'::regclass
                   and tgname = 'dashboard_case_rollup_fact_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_fact_trigger
        after insert or update or delete on operations_case_fact
        for each row execute function refresh_dashboard_case_rollup_read_projection_trigger();
    end if;
    if to_regclass('product_operations_fact_relation') is not null
       and not exists (select 1 from pg_trigger
                        where tgrelid = to_regclass('product_operations_fact_relation')
                          and tgname = 'dashboard_case_rollup_product_relation_trigger'
                          and not tgisinternal) then
        execute 'create trigger dashboard_case_rollup_product_relation_trigger '
                'after insert or update or delete on product_operations_fact_relation '
                'for each row execute function refresh_dashboard_case_rollup_read_projection_trigger()';
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'operations_case_missing_milestone'::regclass
                   and tgname = 'dashboard_case_rollup_missing_milestone_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_missing_milestone_trigger
        after insert or update or delete on operations_case_missing_milestone
        for each row execute function refresh_dashboard_case_rollup_read_projection_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'post_project_mention'::regclass
                   and tgname = 'dashboard_case_rollup_project_mention_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_project_mention_trigger
        after insert or update or delete on post_project_mention
        for each row execute function refresh_dashboard_case_rollup_from_project_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'dashboard_post_read_projection'::regclass
                   and tgname = 'dashboard_case_rollup_post_projection_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_post_projection_trigger
        after update of occurred_at, source_project_name on dashboard_post_read_projection
        for each row execute function refresh_dashboard_case_rollup_from_post_trigger();
    end if;
    if not exists (select 1 from pg_trigger where tgrelid = 'dashboard_post_read_projection'::regclass
                   and tgname = 'dashboard_case_rollup_post_project_code_trigger'
                   and not tgisinternal) then
        create trigger dashboard_case_rollup_post_project_code_trigger
        after update of source_project_code on dashboard_post_read_projection
        for each row execute function refresh_dashboard_case_rollup_from_post_trigger();
    end if;
end
$migration$;

update dashboard_post_read_projection projection
   set source_project_code = post.source_project_code
  from source_post post
 where post.post_id = projection.source_post_id
   and projection.source_project_code is distinct from post.source_project_code;

select refresh_dashboard_case_rollup_read_projection(
    classification.post_id, classification.case_kind_code
)
  from operations_case_classification classification
 where not exists (
     select 1
       from dashboard_case_rollup_read_projection projection
      where projection.source_post_id = classification.post_id
        and projection.case_kind_code = classification.case_kind_code
 );

create index if not exists dashboard_case_rollup_kind_post_idx
    on dashboard_case_rollup_read_projection (case_kind_code, source_post_id);

create index if not exists dashboard_case_rollup_page_idx
    on dashboard_case_rollup_read_projection (
        occurred_at desc, source_post_id desc, case_kind_code desc
    ) include (
        classification_evidence_post_id, summary_text, evidence_text,
        project_name, project_names
    );

create index if not exists dashboard_case_milestone_case_idx
    on dashboard_case_milestone_read_projection (source_post_id, case_kind_code);

create index if not exists dashboard_case_contributor_case_idx
    on dashboard_case_contributor_read_projection (source_post_id, case_kind_code);

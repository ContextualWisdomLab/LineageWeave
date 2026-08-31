-- Migration 0267 / ADR 0272: exact empty-backfill proof for the recovery loop.
--
-- The singleton is a transactionally maintained projection of the same two
-- publication strata used by source_post_eligibility_sql: all active posts,
-- and active posts carrying source context.  The worker therefore avoids a
-- full candidate scan only when the selected stratum proves that every
-- eligible post has a non-succeeded job.  This is an exact proof, not a cache
-- TTL or an inferred estimate.
create table if not exists post_content_recovery_state (
    recovery_state_id smallint primary key check (recovery_state_id = 1),
    active_source_count bigint not null default 0 check (active_source_count >= 0),
    active_job_count bigint not null default 0 check (active_job_count >= 0),
    active_succeeded_job_count bigint not null default 0
        check (active_succeeded_job_count >= 0),
    context_source_count bigint not null default 0 check (context_source_count >= 0),
    context_job_count bigint not null default 0 check (context_job_count >= 0),
    context_succeeded_job_count bigint not null default 0
        check (context_succeeded_job_count >= 0)
);

-- Upgrade the short-lived development version without requiring a reset.
alter table post_content_recovery_state
    add column if not exists active_source_count bigint not null default 0,
    add column if not exists active_job_count bigint not null default 0,
    add column if not exists active_succeeded_job_count bigint not null default 0,
    add column if not exists context_source_count bigint not null default 0,
    add column if not exists context_job_count bigint not null default 0,
    add column if not exists context_succeeded_job_count bigint not null default 0;

-- The pre-0267 development projection used three differently named counters.
-- Keep those columns harmlessly writable when this migration upgrades that
-- transient schema; a fresh database never has them.
do $function$
begin
    if exists (
        select 1 from information_schema.columns
         where table_schema = current_schema()
           and table_name = 'post_content_recovery_state'
           and column_name = 'source_post_count'
    ) then
        alter table post_content_recovery_state
            alter column source_post_count set default 0,
            alter column ingestion_job_count set default 0,
            alter column succeeded_job_count set default 0;
    end if;
end
$function$;

insert into post_content_recovery_state (
    recovery_state_id,
    active_source_count,
    active_job_count,
    active_succeeded_job_count,
    context_source_count,
    context_job_count,
    context_succeeded_job_count
)
select 1,
       count(*) filter (where eligible.active_post),
       count(job.post_id) filter (where eligible.active_post),
       count(job.post_id) filter (
           where eligible.active_post
             and job.status_code = 'post_content_ingestion_succeeded'
       ),
       count(*) filter (where eligible.context_post),
       count(job.post_id) filter (where eligible.context_post),
       count(job.post_id) filter (
           where eligible.context_post
             and job.status_code = 'post_content_ingestion_succeeded'
       )
  from source_post post
  cross join lateral (
      select
          (post.source_draft_code is null or btrim(post.source_draft_code) = '')
          and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')
              as active_post,
          (post.source_draft_code is null or btrim(post.source_draft_code) = '')
          and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')
          and (
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
              or nullif(btrim(post.source_project_name), '') is not null
          ) as context_post
  ) eligible
  left join post_content_ingestion_job job on job.post_id = post.post_id
on conflict (recovery_state_id) do update set
    active_source_count = excluded.active_source_count,
    active_job_count = excluded.active_job_count,
    active_succeeded_job_count = excluded.active_succeeded_job_count,
    context_source_count = excluded.context_source_count,
    context_job_count = excluded.context_job_count,
    context_succeeded_job_count = excluded.context_succeeded_job_count;

create or replace function post_content_recovery_flags(post source_post)
returns table (active_post boolean, context_post boolean)
language sql immutable parallel safe as $function$
    select
        (post.source_draft_code is null or btrim(post.source_draft_code) = '')
        and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = ''),
        (post.source_draft_code is null or btrim(post.source_draft_code) = '')
        and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')
        and (
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
            or nullif(btrim(post.source_project_name), '') is not null
        )
$function$;

create or replace function update_post_content_recovery_source_state()
returns trigger language plpgsql as $function$
declare
    old_active integer := 0;
    old_context integer := 0;
    new_active integer := 0;
    new_context integer := 0;
    old_job integer := 0;
    old_succeeded integer := 0;
    new_job integer := 0;
    new_succeeded integer := 0;
begin
    if tg_op <> 'INSERT' then
        select active_post::integer, context_post::integer
          into old_active, old_context from post_content_recovery_flags(old);
        select 1, (status_code = 'post_content_ingestion_succeeded')::integer
          into old_job, old_succeeded
          from post_content_ingestion_job where post_id = old.post_id;
        old_job := coalesce(old_job, 0);
        old_succeeded := coalesce(old_succeeded, 0);
    end if;
    if tg_op <> 'DELETE' then
        select active_post::integer, context_post::integer
          into new_active, new_context from post_content_recovery_flags(new);
        select 1, (status_code = 'post_content_ingestion_succeeded')::integer
          into new_job, new_succeeded
          from post_content_ingestion_job where post_id = new.post_id;
        new_job := coalesce(new_job, 0);
        new_succeeded := coalesce(new_succeeded, 0);
    end if;
    update post_content_recovery_state set
        active_source_count = active_source_count + new_active - old_active,
        active_job_count = active_job_count + new_active * new_job - old_active * old_job,
        active_succeeded_job_count = active_succeeded_job_count
            + new_active * new_succeeded - old_active * old_succeeded,
        context_source_count = context_source_count + new_context - old_context,
        context_job_count = context_job_count + new_context * new_job - old_context * old_job,
        context_succeeded_job_count = context_succeeded_job_count
            + new_context * new_succeeded - old_context * old_succeeded
     where recovery_state_id = 1;
    return null;
end
$function$;

create or replace function update_post_content_recovery_job_state()
returns trigger language plpgsql as $function$
declare
    post_active integer := 0;
    post_context integer := 0;
    old_job integer := case when tg_op = 'INSERT' then 0 else 1 end;
    new_job integer := case when tg_op = 'DELETE' then 0 else 1 end;
    old_succeeded integer := 0;
    new_succeeded integer := 0;
    target_post_id uuid;
begin
    target_post_id := case when tg_op = 'DELETE' then old.post_id else new.post_id end;
    select flags.active_post::integer, flags.context_post::integer
      into post_active, post_context
      from source_post post
      cross join lateral post_content_recovery_flags(post) flags
     where post.post_id = target_post_id;
    post_active := coalesce(post_active, 0);
    post_context := coalesce(post_context, 0);
    if tg_op <> 'INSERT' then
        old_succeeded := (old.status_code = 'post_content_ingestion_succeeded')::integer;
    end if;
    if tg_op <> 'DELETE' then
        new_succeeded := (new.status_code = 'post_content_ingestion_succeeded')::integer;
    end if;
    update post_content_recovery_state set
        active_job_count = active_job_count + post_active * (new_job - old_job),
        active_succeeded_job_count = active_succeeded_job_count
            + post_active * (new_succeeded - old_succeeded),
        context_job_count = context_job_count + post_context * (new_job - old_job),
        context_succeeded_job_count = context_succeeded_job_count
            + post_context * (new_succeeded - old_succeeded)
     where recovery_state_id = 1;
    return null;
end
$function$;

do $migration$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'source_post'::regclass
           and tgname = 'post_content_recovery_source_state_trigger'
           and not tgisinternal
    ) then
        create trigger post_content_recovery_source_state_trigger
        after insert or delete or update of
            source_draft_code, source_deleted_flag,
            source_author_code, source_author_name,
            source_company_code, source_company_name,
            source_process_unit_code, source_process_unit_name,
            source_sales_pool_code, source_sales_pool_name,
            source_customer_code, source_customer_name,
            source_project_code, source_project_name
        on source_post for each row
        execute function update_post_content_recovery_source_state();
    end if;
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'post_content_ingestion_job'::regclass
           and tgname = 'post_content_recovery_job_state_trigger'
           and not tgisinternal
    ) then
        create trigger post_content_recovery_job_state_trigger
        after insert or delete or update of status_code on post_content_ingestion_job
        for each row execute function update_post_content_recovery_job_state();
    end if;
end
$migration$;

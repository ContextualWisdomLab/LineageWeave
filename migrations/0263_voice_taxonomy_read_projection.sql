-- Migration 0263 / ADR 0272: exact, trigger-maintained Voice read projection.
create table if not exists voice_taxonomy_post_read_projection (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    corporate_entity_id uuid not null,
    process_unit_id uuid,
    visibility_code text not null,
    event_date date not null,
    source_context_present boolean not null,
    membership_count integer not null,
    has_source boolean not null,
    has_derived boolean not null,
    disagreement boolean not null,
    voice_concept_codes text[] not null,
    next_transition_at timestamptz
);

create table if not exists voice_taxonomy_day_read_projection (
    event_date date not null,
    visibility_code text not null,
    corporate_entity_id uuid not null,
    process_unit_key uuid not null,
    source_context_present boolean not null,
    total_eligible bigint not null,
    classified_unique bigint not null,
    multi_membership bigint not null,
    source_count bigint not null,
    derived_count bigint not null,
    unavailable bigint not null,
    disagreement bigint not null,
    category_post_counts jsonb not null,
    next_transition_at timestamptz,
    primary key (
        event_date, visibility_code, corporate_entity_id,
        process_unit_key, source_context_present
    )
);

create table if not exists voice_taxonomy_month_read_projection (
    period_month date not null,
    visibility_code text not null,
    corporate_entity_id uuid not null,
    process_unit_key uuid not null,
    source_context_present boolean not null,
    total_eligible bigint not null,
    classified_unique bigint not null,
    multi_membership bigint not null,
    source_count bigint not null,
    derived_count bigint not null,
    unavailable bigint not null,
    disagreement bigint not null,
    category_post_counts jsonb not null,
    next_transition_at timestamptz,
    primary key (
        period_month, visibility_code, corporate_entity_id, process_unit_key,
        source_context_present
    )
);

create or replace function refresh_voice_taxonomy_post_read_projection(target_post_id uuid)
returns void language plpgsql as $function$
begin
    delete from voice_taxonomy_post_read_projection where post_id = target_post_id;

    insert into voice_taxonomy_post_read_projection (
        post_id, corporate_entity_id, process_unit_id, visibility_code,
        event_date, source_context_present, membership_count, has_source,
        has_derived, disagreement, voice_concept_codes, next_transition_at
    )
    select post.post_id, post.corporate_entity_id, post.process_unit_id,
           post.visibility_code,
           timezone('Asia/Seoul', coalesce(post.event_occurred_at, post.created_at))::date,
           (nullif(btrim(post.source_author_code), '') is not null
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
            or nullif(btrim(post.source_project_name), '') is not null),
           coalesce(assertion.membership_count, 0),
           coalesce(assertion.has_source, false),
           coalesce(assertion.has_derived, false),
           coalesce(assertion.has_source, false)
             and coalesce(assertion.has_derived, false)
             and assertion.source_codes is distinct from assertion.derived_codes,
           coalesce(assertion.voice_codes, array[]::text[]),
           assertion.next_transition_at
      from source_post post
      left join lateral (
          select (count(distinct voice_concept_code) filter (where is_active))::integer
                     as membership_count,
                 bool_or(assertion_status_code = 'source') filter (where is_active)
                     as has_source,
                 bool_or(assertion_status_code = 'derived') filter (where is_active)
                     as has_derived,
                 array_agg(distinct voice_concept_code order by voice_concept_code)
                     filter (where is_active) as voice_codes,
                 array_agg(distinct voice_concept_code order by voice_concept_code)
                     filter (where is_active and assertion_status_code = 'source')
                     as source_codes,
                 array_agg(distinct voice_concept_code order by voice_concept_code)
                     filter (where is_active and assertion_status_code = 'derived')
                     as derived_codes,
                 min(transition_at) filter (where transition_at > clock_timestamp())
                     as next_transition_at
            from (
                select assertion.*,
                       (assertion.valid_from is null or assertion.valid_from <= clock_timestamp())
                       and (assertion.valid_to is null or assertion.valid_to > clock_timestamp())
                           as is_active,
                       case
                           when assertion.valid_from > clock_timestamp()
                                and (assertion.valid_to is null
                                     or assertion.valid_from <= assertion.valid_to)
                               then assertion.valid_from
                           when assertion.valid_to > clock_timestamp() then assertion.valid_to
                       end as transition_at
                  from post_voice_classification_assertion assertion
                 where assertion.post_id = post.post_id
            ) assertion_window
      ) assertion on true
     where post.post_id = target_post_id
       and (post.source_draft_code is null or btrim(post.source_draft_code) = '')
       and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '');
end
$function$;

create or replace function add_voice_taxonomy_category_counts(left_counts jsonb, right_counts jsonb)
returns jsonb language sql immutable as $function$
    select coalesce(jsonb_object_agg(voice_code, post_count)
                        filter (where post_count <> 0), '{}'::jsonb)
      from (
          select voice_code, sum(post_count) as post_count
            from (
                select key as voice_code, value::text::bigint as post_count
                  from jsonb_each(coalesce(left_counts, '{}'::jsonb))
                union all
                select key, value::text::bigint
                  from jsonb_each(coalesce(right_counts, '{}'::jsonb))
            ) count_delta
           group by voice_code
      ) combined
$function$;

create or replace function voice_taxonomy_category_delta(voice_codes text[], direction bigint)
returns jsonb language sql immutable as $function$
    select coalesce(jsonb_object_agg(voice_code, direction), '{}'::jsonb)
      from unnest(voice_codes) voice_code
$function$;

create or replace function adjust_voice_taxonomy_rollups(
    projection voice_taxonomy_post_read_projection,
    direction bigint
) returns void language plpgsql as $function$
declare
    process_key constant uuid := coalesce(
        projection.process_unit_id,
        '00000000-0000-0000-0000-000000000000'::uuid
    );
    category_delta jsonb := voice_taxonomy_category_delta(
        projection.voice_concept_codes, direction
    );
begin
    insert into voice_taxonomy_day_read_projection values (
        projection.event_date, projection.visibility_code,
        projection.corporate_entity_id, process_key,
        projection.source_context_present, direction,
        direction * (projection.membership_count = 1)::integer,
        direction * (projection.membership_count > 1)::integer,
        direction * projection.has_source::integer,
        direction * projection.has_derived::integer,
        direction * (projection.membership_count = 0)::integer,
        direction * projection.disagreement::integer,
        category_delta, projection.next_transition_at
    ) on conflict (
        event_date, visibility_code, corporate_entity_id,
        process_unit_key, source_context_present
    ) do update set
        total_eligible = voice_taxonomy_day_read_projection.total_eligible + excluded.total_eligible,
        classified_unique = voice_taxonomy_day_read_projection.classified_unique + excluded.classified_unique,
        multi_membership = voice_taxonomy_day_read_projection.multi_membership + excluded.multi_membership,
        source_count = voice_taxonomy_day_read_projection.source_count + excluded.source_count,
        derived_count = voice_taxonomy_day_read_projection.derived_count + excluded.derived_count,
        unavailable = voice_taxonomy_day_read_projection.unavailable + excluded.unavailable,
        disagreement = voice_taxonomy_day_read_projection.disagreement + excluded.disagreement,
        category_post_counts = add_voice_taxonomy_category_counts(
            voice_taxonomy_day_read_projection.category_post_counts,
            excluded.category_post_counts
        );

    insert into voice_taxonomy_month_read_projection values (
        date_trunc('month', projection.event_date)::date,
        projection.visibility_code, projection.corporate_entity_id, process_key,
        projection.source_context_present, direction,
        direction * (projection.membership_count = 1)::integer,
        direction * (projection.membership_count > 1)::integer,
        direction * projection.has_source::integer,
        direction * projection.has_derived::integer,
        direction * (projection.membership_count = 0)::integer,
        direction * projection.disagreement::integer,
        category_delta, projection.next_transition_at
    ) on conflict (
        period_month, visibility_code, corporate_entity_id, process_unit_key,
        source_context_present
    ) do update set
        total_eligible = voice_taxonomy_month_read_projection.total_eligible + excluded.total_eligible,
        classified_unique = voice_taxonomy_month_read_projection.classified_unique + excluded.classified_unique,
        multi_membership = voice_taxonomy_month_read_projection.multi_membership + excluded.multi_membership,
        source_count = voice_taxonomy_month_read_projection.source_count + excluded.source_count,
        derived_count = voice_taxonomy_month_read_projection.derived_count + excluded.derived_count,
        unavailable = voice_taxonomy_month_read_projection.unavailable + excluded.unavailable,
        disagreement = voice_taxonomy_month_read_projection.disagreement + excluded.disagreement,
        category_post_counts = add_voice_taxonomy_category_counts(
            voice_taxonomy_month_read_projection.category_post_counts,
            excluded.category_post_counts
        );

    delete from voice_taxonomy_day_read_projection where total_eligible = 0;
    delete from voice_taxonomy_month_read_projection where total_eligible = 0;

    update voice_taxonomy_day_read_projection rollup
       set next_transition_at = (
           select min(candidate.next_transition_at)
             from voice_taxonomy_post_read_projection candidate
            where candidate.event_date = projection.event_date
              and candidate.visibility_code = projection.visibility_code
              and candidate.corporate_entity_id = projection.corporate_entity_id
              and candidate.process_unit_id is not distinct from projection.process_unit_id
              and candidate.source_context_present = projection.source_context_present
       )
     where rollup.event_date = projection.event_date
       and rollup.visibility_code = projection.visibility_code
       and rollup.corporate_entity_id = projection.corporate_entity_id
       and rollup.process_unit_key = process_key
       and rollup.source_context_present = projection.source_context_present;
    update voice_taxonomy_month_read_projection rollup
       set next_transition_at = (
           select min(candidate.next_transition_at)
             from voice_taxonomy_post_read_projection candidate
            where candidate.visibility_code = projection.visibility_code
              and candidate.corporate_entity_id = projection.corporate_entity_id
              and candidate.process_unit_id is not distinct from projection.process_unit_id
              and candidate.source_context_present = projection.source_context_present
              and candidate.event_date >= date_trunc('month', projection.event_date)::date
              and candidate.event_date <
                  (date_trunc('month', projection.event_date) + interval '1 month')::date
       )
     where rollup.period_month = date_trunc('month', projection.event_date)::date
       and rollup.visibility_code = projection.visibility_code
       and rollup.corporate_entity_id = projection.corporate_entity_id
       and rollup.process_unit_key = process_key
       and rollup.source_context_present = projection.source_context_present;
end
$function$;

create index if not exists voice_taxonomy_post_transition_day_idx
    on voice_taxonomy_post_read_projection (
        event_date, visibility_code, corporate_entity_id, process_unit_id,
        source_context_present, event_date, next_transition_at
    );
create index if not exists voice_taxonomy_post_transition_month_idx
    on voice_taxonomy_post_read_projection (
        visibility_code, corporate_entity_id, process_unit_id,
        source_context_present, next_transition_at
    );

create or replace function reconcile_voice_taxonomy_post_read_projection(target_post_id uuid)
returns void language plpgsql as $function$
declare
    old_row voice_taxonomy_post_read_projection%rowtype;
    new_row voice_taxonomy_post_read_projection%rowtype;
begin
    select * into old_row from voice_taxonomy_post_read_projection where post_id = target_post_id;
    perform refresh_voice_taxonomy_post_read_projection(target_post_id);
    select * into new_row from voice_taxonomy_post_read_projection where post_id = target_post_id;
    if old_row.post_id is not null then
        perform adjust_voice_taxonomy_rollups(old_row, -1);
    end if;
    if new_row.post_id is not null then
        perform adjust_voice_taxonomy_rollups(new_row, 1);
    end if;
end
$function$;

create or replace function reconcile_due_voice_taxonomy_read_projections()
returns bigint language plpgsql as $function$
declare
    due_post record;
    reconciled bigint := 0;
begin
    for due_post in
        select post_id
          from voice_taxonomy_post_read_projection
         where next_transition_at <= clock_timestamp()
         order by next_transition_at, post_id
         for update skip locked
    loop
        perform reconcile_voice_taxonomy_post_read_projection(due_post.post_id);
        reconciled := reconciled + 1;
    end loop;
    return reconciled;
end
$function$;

create or replace function reconcile_voice_taxonomy_read_projection()
returns trigger language plpgsql as $function$
begin
    perform reconcile_voice_taxonomy_post_read_projection(coalesce(new.post_id, old.post_id));
    perform pg_notify('voice_taxonomy_transition', '');
    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end
$function$;

do $trigger$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'source_post'::regclass
           and tgname = 'voice_taxonomy_source_read_reconcile'
           and not tgisinternal
    ) then
        create trigger voice_taxonomy_source_read_reconcile
        after insert or update or delete on source_post
        for each row execute function reconcile_voice_taxonomy_read_projection();
    end if;
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'post_voice_classification_assertion'::regclass
           and tgname = 'voice_taxonomy_assertion_read_reconcile'
           and not tgisinternal
    ) then
        create trigger voice_taxonomy_assertion_read_reconcile
        after insert or update or delete on post_voice_classification_assertion
        for each row execute function reconcile_voice_taxonomy_read_projection();
    end if;
end
$trigger$;

do $backfill$
declare post_row record;
begin
    if not exists (
        select 1 from data_migration_completion
         where migration_code = '0263_voice_taxonomy_read_projection'
    ) then
        truncate voice_taxonomy_post_read_projection,
                 voice_taxonomy_day_read_projection,
                 voice_taxonomy_month_read_projection;
        for post_row in select post_id from source_post loop
            perform refresh_voice_taxonomy_post_read_projection(post_row.post_id);
        end loop;

        insert into voice_taxonomy_day_read_projection
        select event_date, visibility_code, corporate_entity_id,
       coalesce(process_unit_id, '00000000-0000-0000-0000-000000000000'::uuid),
       source_context_present, count(*),
       count(*) filter (where membership_count = 1),
       count(*) filter (where membership_count > 1),
       count(*) filter (where has_source), count(*) filter (where has_derived),
       count(*) filter (where membership_count = 0), count(*) filter (where disagreement),
       jsonb_strip_nulls(jsonb_build_object(
           'voc', nullif(count(*) filter (where 'voc' = any(voice_concept_codes)), 0),
           'vocc', nullif(count(*) filter (where 'vocc' = any(voice_concept_codes)), 0),
           'voco', nullif(count(*) filter (where 'voco' = any(voice_concept_codes)), 0),
           'vom', nullif(count(*) filter (where 'vom' = any(voice_concept_codes)), 0),
           'vop', nullif(count(*) filter (where 'vop' = any(voice_concept_codes)), 0),
           'vos', nullif(count(*) filter (where 'vos' = any(voice_concept_codes)), 0),
           'voe', nullif(count(*) filter (where 'voe' = any(voice_concept_codes)), 0),
           'vob', nullif(count(*) filter (where 'vob' = any(voice_concept_codes)), 0),
           'vor', nullif(count(*) filter (where 'vor' = any(voice_concept_codes)), 0),
           'voi', nullif(count(*) filter (where 'voi' = any(voice_concept_codes)), 0),
           'voso', nullif(count(*) filter (where 'voso' = any(voice_concept_codes)), 0),
           'vops', nullif(count(*) filter (where 'vops' = any(voice_concept_codes)), 0)
       )), min(next_transition_at)
          from voice_taxonomy_post_read_projection
         group by event_date, visibility_code, corporate_entity_id, process_unit_id,
                  source_context_present;

        insert into voice_taxonomy_month_read_projection
        select date_trunc('month', event_date)::date, visibility_code, corporate_entity_id,
       coalesce(process_unit_id, '00000000-0000-0000-0000-000000000000'::uuid),
       source_context_present, count(*),
       count(*) filter (where membership_count = 1),
       count(*) filter (where membership_count > 1),
       count(*) filter (where has_source), count(*) filter (where has_derived),
       count(*) filter (where membership_count = 0), count(*) filter (where disagreement),
       jsonb_strip_nulls(jsonb_build_object(
           'voc', nullif(count(*) filter (where 'voc' = any(voice_concept_codes)), 0),
           'vocc', nullif(count(*) filter (where 'vocc' = any(voice_concept_codes)), 0),
           'voco', nullif(count(*) filter (where 'voco' = any(voice_concept_codes)), 0),
           'vom', nullif(count(*) filter (where 'vom' = any(voice_concept_codes)), 0),
           'vop', nullif(count(*) filter (where 'vop' = any(voice_concept_codes)), 0),
           'vos', nullif(count(*) filter (where 'vos' = any(voice_concept_codes)), 0),
           'voe', nullif(count(*) filter (where 'voe' = any(voice_concept_codes)), 0),
           'vob', nullif(count(*) filter (where 'vob' = any(voice_concept_codes)), 0),
           'vor', nullif(count(*) filter (where 'vor' = any(voice_concept_codes)), 0),
           'voi', nullif(count(*) filter (where 'voi' = any(voice_concept_codes)), 0),
           'voso', nullif(count(*) filter (where 'voso' = any(voice_concept_codes)), 0),
           'vops', nullif(count(*) filter (where 'vops' = any(voice_concept_codes)), 0)
       )), min(next_transition_at)
          from voice_taxonomy_post_read_projection
         group by date_trunc('month', event_date)::date, visibility_code,
                  corporate_entity_id, process_unit_id,
                  source_context_present;

        insert into data_migration_completion (migration_code)
        values ('0263_voice_taxonomy_read_projection');
    end if;
end
$backfill$;

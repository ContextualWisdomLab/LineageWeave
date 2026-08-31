-- Migration 0269 / ADR 0272: keep normalized body-search values off the wide
-- source heap so an indexed lookup does not decompress and normalize TOAST data.
create table if not exists data_migration_completion (
    migration_code text primary key,
    completed_at timestamptz not null default current_timestamp
);

alter table post_list_read_projection
    add column if not exists post_body_search_prefix text not null default '',
    add column if not exists post_body_search_vector tsvector not null default ''::tsvector,
    add column if not exists search_source_exact_text text not null default '',
    add column if not exists search_related_master_exact_text text not null default '',
    add column if not exists search_normalized_post_id text not null default '',
    add column if not exists search_source_record_key text not null default '';

create index concurrently if not exists post_list_body_search_prefix_trgm_idx
    on post_list_read_projection using gin (post_body_search_prefix gin_trgm_ops);

create index concurrently if not exists post_list_body_search_vector_idx
    on post_list_read_projection using gin (post_body_search_vector);

create index concurrently if not exists post_list_search_source_exact_trgm_idx
    on post_list_read_projection using gin (search_source_exact_text gin_trgm_ops);
create index concurrently if not exists post_list_search_related_master_trgm_idx
    on post_list_read_projection using gin (search_related_master_exact_text gin_trgm_ops);
create index concurrently if not exists post_list_search_post_id_trgm_idx
    on post_list_read_projection using gin (search_normalized_post_id gin_trgm_ops);
create index concurrently if not exists post_list_search_record_key_trgm_idx
    on post_list_read_projection using gin (search_source_record_key gin_trgm_ops);

create or replace function refresh_post_list_read_projection()
returns trigger language plpgsql as $function$
declare
    search_text text := source_post_search_text(new.post_body);
begin
    insert into post_list_read_projection (
        post_id, post_body_excerpt, post_body_truncated,
        post_body_character_count, post_body_byte_count,
        post_body_search_prefix, post_body_search_vector
    ) values (
        new.post_id,
        btrim(left(search_text, 420)),
        char_length(coalesce(new.post_body, '')) > 420,
        char_length(coalesce(new.post_body, '')),
        octet_length(coalesce(new.post_body, '')),
        lower(left(search_text, 16384)),
        to_tsvector('simple', search_text)
    )
    on conflict (post_id) do update set
        post_body_excerpt = excluded.post_body_excerpt,
        post_body_truncated = excluded.post_body_truncated,
        post_body_character_count = excluded.post_body_character_count,
        post_body_byte_count = excluded.post_body_byte_count,
        post_body_search_prefix = excluded.post_body_search_prefix,
        post_body_search_vector = excluded.post_body_search_vector;
    return null;
end
$function$;

create or replace function refresh_post_list_search_metadata_projection()
returns trigger language plpgsql as $function$
begin
    insert into post_list_read_projection (
        post_id, post_body_excerpt, post_body_truncated,
        post_body_character_count, post_body_byte_count,
        search_source_exact_text,
        search_normalized_post_id, search_source_record_key
    ) values (
        new.post_id, '', false, 0, 0,
        lower(concat_ws(chr(31),
            new.post_title, new.thread_group_key, new.secondary_grouping_key,
            new.source_stage_code, new.source_detail_state_code,
            new.source_draft_code, new.source_deleted_flag,
            new.source_author_code, new.source_author_name,
            new.source_company_code, new.source_company_name,
            new.source_process_unit_code, new.source_process_unit_name,
            new.source_sales_pool_code, new.source_sales_pool_name,
            new.source_customer_code, new.source_customer_name,
            new.source_project_code, new.source_project_name,
            new.source_system_code, new.source_record_key,
            replace(new.post_id::text, '-', '')
        )),
        replace(new.post_id::text, '-', ''),
        lower(coalesce(new.source_record_key, ''))
    )
    on conflict (post_id) do update set
        search_source_exact_text = excluded.search_source_exact_text,
        search_normalized_post_id = excluded.search_normalized_post_id,
        search_source_record_key = excluded.search_source_record_key;
    return null;
end
$function$;

drop trigger if exists post_list_search_metadata_projection_trigger on source_post;
create trigger post_list_search_metadata_projection_trigger
after insert or update of
    post_title, thread_group_key, secondary_grouping_key,
    source_stage_code, source_detail_state_code, source_draft_code,
    source_deleted_flag, source_author_code, source_author_name,
    source_company_code, source_company_name, source_process_unit_code,
    source_process_unit_name, source_sales_pool_code, source_sales_pool_name,
    source_customer_code, source_customer_name, source_project_code,
    source_project_name, source_system_code, source_record_key
on source_post for each row
execute function refresh_post_list_search_metadata_projection();

do $backfill$
begin
if not exists (
    select 1 from data_migration_completion
     where migration_code = '0269_post_body_search_read_projection'
) then
insert into post_list_read_projection (
    post_id, post_body_excerpt, post_body_truncated,
    post_body_character_count, post_body_byte_count,
    post_body_search_prefix, post_body_search_vector
)
select post_id, btrim(left(search_text, 420)),
       char_length(coalesce(post_body, '')) > 420,
       char_length(coalesce(post_body, '')),
       octet_length(coalesce(post_body, '')),
       lower(left(search_text, 16384)),
       to_tsvector('simple', search_text)
  from (
      select post_id, post_body, source_post_search_text(post_body) as search_text
        from source_post
  ) normalized
on conflict (post_id) do update set
    post_body_excerpt = excluded.post_body_excerpt,
    post_body_truncated = excluded.post_body_truncated,
    post_body_character_count = excluded.post_body_character_count,
    post_body_byte_count = excluded.post_body_byte_count,
    post_body_search_prefix = excluded.post_body_search_prefix,
    post_body_search_vector = excluded.post_body_search_vector;

insert into data_migration_completion (migration_code)
values ('0269_post_body_search_read_projection');
end if;
end
$backfill$;

update post_list_read_projection projection
   set search_source_exact_text = lower(concat_ws(chr(31),
           source.post_title, source.thread_group_key, source.secondary_grouping_key,
           source.source_stage_code, source.source_detail_state_code,
           source.source_draft_code, source.source_deleted_flag,
           source.source_author_code, source.source_author_name,
           source.source_company_code, source.source_company_name,
           source.source_process_unit_code, source.source_process_unit_name,
           source.source_sales_pool_code, source.source_sales_pool_name,
           source.source_customer_code, source.source_customer_name,
           source.source_project_code, source.source_project_name,
           source.source_system_code, source.source_record_key,
           replace(source.post_id::text, '-', '')
       )),
       search_normalized_post_id = replace(source.post_id::text, '-', ''),
       search_source_record_key = lower(coalesce(source.source_record_key, ''))
  from source_post source
 where source.post_id = projection.post_id
   and projection.search_source_exact_text = '';

create or replace function post_search_related_master_text(target_post_id uuid)
returns text language sql stable as $function$
select lower(concat_ws(chr(31),
    customer.entity_name, customer.corporate_entity_code,
    process.process_unit_name, process.process_unit_code,
    author.display_name, author.email_address,
    (select string_agg(concat_ws(chr(31), affiliated.entity_name,
                                affiliated.corporate_entity_code), chr(31)
                       order by affiliated.corporate_entity_id)
       from account_affiliation affiliation
       join corporate_entity affiliated
         on affiliated.corporate_entity_id = affiliation.corporate_entity_id
      where affiliation.user_account_id = source.author_account_id),
    (select string_agg(concat_ws(chr(31), project.project_key, project.project_name,
                                project.evidence_text, project.ontology_iri), chr(31)
                       order by project.project_key, project.ontology_iri)
       from post_project_mention project where project.post_id = source.post_id),
    (select string_agg(concat_ws(chr(31), role.actor_name, role.responsibility,
                                role.affiliated_organization_name), chr(31)
                       order by role.actor_name)
       from post_summary_role role where role.post_id = source.post_id),
    (select string_agg(person.person_name, chr(31) order by person.person_id)
       from post_person_mention mention
       join cataloged_person person on person.person_id = mention.person_id
      where mention.post_id = source.post_id),
    (select string_agg(summary.korean_summary, chr(31) order by summary.computed_at)
       from post_summary_result summary where summary.post_id = source.post_id),
    (select string_agg(event.event_text, chr(31) order by event.event_ordinal)
       from post_summary_event event where event.post_id = source.post_id)
))
  from source_post source
  left join corporate_entity customer
    on customer.corporate_entity_id = source.corporate_entity_id
  left join process_unit process on process.process_unit_id = source.process_unit_id
  left join user_account author on author.user_account_id = source.author_account_id
 where source.post_id = target_post_id
$function$;

create or replace function refresh_post_search_related_master(target_post_id uuid)
returns void language sql as $function$
update post_list_read_projection
   set search_related_master_exact_text =
       coalesce(post_search_related_master_text(target_post_id), '')
 where post_id = target_post_id
$function$;

create or replace function reconcile_post_search_related_master()
returns trigger language plpgsql as $function$
declare
    affected_post_id uuid;
begin
    if tg_table_name = 'source_post' then
        if tg_op <> 'DELETE' then
            perform refresh_post_search_related_master(new.post_id);
        end if;
    elsif tg_table_name in (
        'post_project_mention', 'post_summary_role', 'post_person_mention',
        'post_summary_result', 'post_summary_event'
    ) then
        perform refresh_post_search_related_master(
            case when tg_op = 'DELETE' then old.post_id else new.post_id end
        );
    elsif tg_table_name = 'cataloged_person' then
        for affected_post_id in
            select distinct mention.post_id from post_person_mention mention
             where mention.person_id in (old.person_id, new.person_id)
        loop
            perform refresh_post_search_related_master(affected_post_id);
        end loop;
    elsif tg_table_name = 'corporate_entity' then
        for affected_post_id in
            select source.post_id from source_post source
             where source.corporate_entity_id in (
                       old.corporate_entity_id, new.corporate_entity_id
                   )
                or exists (
                    select 1 from account_affiliation affiliation
                     where affiliation.user_account_id = source.author_account_id
                       and affiliation.corporate_entity_id in (
                           old.corporate_entity_id, new.corporate_entity_id
                       )
                )
        loop
            perform refresh_post_search_related_master(affected_post_id);
        end loop;
    elsif tg_table_name = 'process_unit' then
        for affected_post_id in
            select source.post_id from source_post source
             where source.process_unit_id in (old.process_unit_id, new.process_unit_id)
        loop
            perform refresh_post_search_related_master(affected_post_id);
        end loop;
    elsif tg_table_name = 'user_account' then
        for affected_post_id in
            select source.post_id from source_post source
             where source.author_account_id in (
                 old.user_account_id, new.user_account_id
             )
        loop
            perform refresh_post_search_related_master(affected_post_id);
        end loop;
    elsif tg_table_name = 'account_affiliation' then
        for affected_post_id in
            select source.post_id from source_post source
             where source.author_account_id in (
                 old.user_account_id, new.user_account_id
             )
        loop
            perform refresh_post_search_related_master(affected_post_id);
        end loop;
    end if;
    return null;
end
$function$;

do $triggers$
declare
    relation_name text;
begin
    foreach relation_name in array array[
        'source_post', 'post_project_mention', 'post_summary_role',
        'post_person_mention', 'post_summary_result', 'post_summary_event',
        'cataloged_person', 'corporate_entity', 'process_unit', 'user_account',
        'account_affiliation'
    ] loop
        execute format(
            'drop trigger if exists post_search_related_master_reconcile on %I',
            relation_name
        );
        execute format(
            'create trigger post_search_related_master_reconcile '
            'after insert or update or delete on %I for each row '
            'execute function reconcile_post_search_related_master()',
            relation_name
        );
    end loop;
end
$triggers$;

do $related_backfill$
begin
if not exists (
    select 1 from data_migration_completion
     where migration_code = '0269_post_search_related_master_projection'
) then
    update post_list_read_projection
       set search_related_master_exact_text =
           coalesce(post_search_related_master_text(post_id), '');
    insert into data_migration_completion (migration_code)
    values ('0269_post_search_related_master_projection');
end if;
end
$related_backfill$;

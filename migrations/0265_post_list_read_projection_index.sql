-- Migration 0265 / ADR 0272: serve exact Post list counts and filter options
-- from a narrow maintained access path instead of the wide source heap.
create index concurrently if not exists source_post_active_context_page_idx
    on source_post (
        created_at desc,
        post_id desc
    ) include (
        visibility_code, corporate_entity_id, process_unit_id,
        post_title, voc_type_code
    )
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
      and (
          nullif(btrim(source_author_code), '') is not null
          or nullif(btrim(source_author_name), '') is not null
          or nullif(btrim(source_company_code), '') is not null
          or nullif(btrim(source_company_name), '') is not null
          or nullif(btrim(source_process_unit_code), '') is not null
          or nullif(btrim(source_process_unit_name), '') is not null
          or nullif(btrim(source_sales_pool_code), '') is not null
          or nullif(btrim(source_sales_pool_name), '') is not null
          or nullif(btrim(source_customer_code), '') is not null
          or nullif(btrim(source_customer_name), '') is not null
          or nullif(btrim(source_project_code), '') is not null
          or nullif(btrim(source_project_name), '') is not null
      );

create index concurrently if not exists source_post_active_page_idx
    on source_post (
        created_at desc,
        post_id desc
    ) include (
        visibility_code, corporate_entity_id, process_unit_id,
        post_title, voc_type_code
    )
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '');

create index concurrently if not exists source_post_active_context_title_page_idx
    on source_post (
        lower(coalesce(post_title, '')),
        created_at desc,
        post_id desc
    ) include (visibility_code, corporate_entity_id, process_unit_id, voc_type_code)
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
      and (
          nullif(btrim(source_author_code), '') is not null
          or nullif(btrim(source_author_name), '') is not null
          or nullif(btrim(source_company_code), '') is not null
          or nullif(btrim(source_company_name), '') is not null
          or nullif(btrim(source_process_unit_code), '') is not null
          or nullif(btrim(source_process_unit_name), '') is not null
          or nullif(btrim(source_sales_pool_code), '') is not null
          or nullif(btrim(source_sales_pool_name), '') is not null
          or nullif(btrim(source_customer_code), '') is not null
          or nullif(btrim(source_customer_name), '') is not null
          or nullif(btrim(source_project_code), '') is not null
          or nullif(btrim(source_project_name), '') is not null
      );

create index concurrently if not exists source_post_active_title_page_idx
    on source_post (
        lower(coalesce(post_title, '')),
        created_at desc,
        post_id desc
    ) include (visibility_code, corporate_entity_id, process_unit_id, voc_type_code)
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '');

create table if not exists post_list_read_projection (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    post_body_excerpt text not null,
    post_body_truncated boolean not null,
    post_body_character_count bigint not null,
    post_body_byte_count bigint not null
);

alter table post_list_read_projection
    add column if not exists post_body_character_count bigint not null default 0,
    add column if not exists post_body_byte_count bigint not null default 0;

create or replace function refresh_post_list_read_projection()
returns trigger language plpgsql as $function$
begin
    insert into post_list_read_projection (
        post_id, post_body_excerpt, post_body_truncated,
        post_body_character_count, post_body_byte_count
    ) values (
        new.post_id,
        btrim(left(source_post_search_text(new.post_body), 420)),
        char_length(coalesce(new.post_body, '')) > 420,
        char_length(coalesce(new.post_body, '')),
        octet_length(coalesce(new.post_body, ''))
    )
    on conflict (post_id) do update set
        post_body_excerpt = excluded.post_body_excerpt,
        post_body_truncated = excluded.post_body_truncated,
        post_body_character_count = excluded.post_body_character_count,
        post_body_byte_count = excluded.post_body_byte_count;
    return null;
end
$function$;

do $migration$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'source_post'::regclass
           and tgname = 'post_list_source_read_projection_trigger'
           and not tgisinternal
    ) then
        create trigger post_list_source_read_projection_trigger
        after insert or update of post_body on source_post
        for each row execute function refresh_post_list_read_projection();
    end if;
end
$migration$;

insert into post_list_read_projection (
    post_id, post_body_excerpt, post_body_truncated,
    post_body_character_count, post_body_byte_count
)
select post_id, btrim(left(source_post_search_text(post_body), 420)),
       char_length(coalesce(post_body, '')) > 420,
       char_length(coalesce(post_body, '')),
       octet_length(coalesce(post_body, ''))
  from source_post
on conflict (post_id) do nothing;

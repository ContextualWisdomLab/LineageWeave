-- ADR 0277: exact, transaction-maintained Customer Master group counts.
create table if not exists customer_master_post_read_projection (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    post_title text not null,
    created_at timestamptz not null,
    visibility_code text not null,
    corporate_entity_id uuid,
    process_unit_id uuid,
    customer_code_key text not null,
    customer_name_group_key text not null,
    customer_name text,
    author_code text,
    author_name text,
    author_account_id uuid not null,
    account_display_name text not null
);
alter table customer_master_post_read_projection
    add column if not exists customer_name text;
create index if not exists customer_master_post_customer_related_idx
    on customer_master_post_read_projection (
        customer_code_key, customer_name_group_key, created_at desc, post_id desc
    ) include (post_title, visibility_code, corporate_entity_id, process_unit_id);
create index if not exists customer_master_post_author_related_idx
    on customer_master_post_read_projection (
        author_code, author_account_id, account_display_name, created_at desc, post_id desc
    ) include (post_title, author_name, visibility_code, corporate_entity_id, process_unit_id)
    where author_code is not null;

create table if not exists customer_hint_group_read_projection (
    visibility_code text not null,
    corporate_entity_key uuid not null,
    process_unit_key uuid not null,
    customer_code_key text not null,
    customer_name_group_key text not null,
    customer_name text,
    post_count bigint not null check (post_count >= 0),
    primary key (
        visibility_code, corporate_entity_key, process_unit_key,
        customer_code_key, customer_name_group_key
    )
);

create index if not exists customer_hint_group_read_rank_idx
    on customer_hint_group_read_projection (
        visibility_code, corporate_entity_key, process_unit_key,
        post_count desc, customer_code_key, customer_name_group_key
    );

create table if not exists author_hint_group_read_projection (
    visibility_code text not null,
    corporate_entity_key uuid not null,
    process_unit_key uuid not null,
    author_code text not null,
    author_account_id uuid not null,
    account_display_name text not null,
    author_name text,
    post_count bigint not null check (post_count >= 0),
    primary key (
        visibility_code, corporate_entity_key, process_unit_key,
        author_code, author_account_id, account_display_name
    )
);

create index if not exists author_hint_group_read_rank_idx
    on author_hint_group_read_projection (
        visibility_code, corporate_entity_key, process_unit_key,
        post_count desc, author_code, author_account_id, account_display_name
    );

create index concurrently if not exists source_post_customer_hint_related_idx
    on source_post (
        coalesce(nullif(btrim(source_customer_code), ''), ''),
        coalesce(case when nullif(btrim(source_customer_code), '') is null
                      then nullif(btrim(source_customer_name), '') end, ''),
        created_at desc, post_id desc
    ) include (post_title, visibility_code, corporate_entity_id, process_unit_id)
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
      and (nullif(btrim(source_customer_code), '') is not null
           or nullif(btrim(source_customer_name), '') is not null);

create index concurrently if not exists source_post_author_hint_related_idx
    on source_post (btrim(source_author_code), author_account_id,
                    created_at desc, post_id desc)
    include (post_title, source_author_name, visibility_code,
             corporate_entity_id, process_unit_id)
    where (source_draft_code is null or btrim(source_draft_code) = '')
      and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
      and nullif(btrim(source_author_code), '') is not null;

create or replace function customer_master_projection_apply(
    post source_post, delta integer
) returns void language plpgsql as $function$
declare
    entity_key constant uuid := '00000000-0000-0000-0000-000000000000';
    v_customer_code text;
    v_customer_name text;
    v_customer_name_group text;
    v_author_code text;
    v_author_name text;
    account_name text;
begin
    if delta < 0 then
        delete from customer_master_post_read_projection where post_id = post.post_id;
    end if;
    if not ((post.source_draft_code is null or btrim(post.source_draft_code) = '')
        and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')) then
        return;
    end if;
    v_customer_code := nullif(btrim(post.source_customer_code), '');
    v_customer_name := nullif(btrim(post.source_customer_name), '');
    v_customer_name_group := case when v_customer_code is null then v_customer_name end;
    if v_customer_code is not null or v_customer_name is not null then
        insert into customer_hint_group_read_projection values (
            post.visibility_code,
            coalesce(post.corporate_entity_id, entity_key),
            coalesce(post.process_unit_id, entity_key),
            coalesce(v_customer_code, ''), coalesce(v_customer_name_group, ''),
            v_customer_name, greatest(delta, 0)
        ) on conflict (
            visibility_code, corporate_entity_key, process_unit_key,
            customer_code_key, customer_name_group_key
        ) do update set
            post_count = greatest(
                customer_hint_group_read_projection.post_count + delta, 0
            ),
            customer_name = case when delta > 0 then coalesce(greatest(
                customer_hint_group_read_projection.customer_name,
                excluded.customer_name
            ), customer_hint_group_read_projection.customer_name, excluded.customer_name)
            else customer_hint_group_read_projection.customer_name end;
        delete from customer_hint_group_read_projection where post_count <= 0;
        if delta < 0 then
            update customer_hint_group_read_projection grouped
               set customer_name = (
                   select max(remaining.customer_name)
                     from customer_master_post_read_projection remaining
                    where remaining.visibility_code = grouped.visibility_code
                      and coalesce(remaining.corporate_entity_id, entity_key) = grouped.corporate_entity_key
                      and coalesce(remaining.process_unit_id, entity_key) = grouped.process_unit_key
                      and remaining.customer_code_key = grouped.customer_code_key
                      and remaining.customer_name_group_key = grouped.customer_name_group_key
               )
             where grouped.visibility_code = post.visibility_code
               and grouped.corporate_entity_key = coalesce(post.corporate_entity_id, entity_key)
               and grouped.process_unit_key = coalesce(post.process_unit_id, entity_key)
               and grouped.customer_code_key = coalesce(v_customer_code, '')
               and grouped.customer_name_group_key = coalesce(v_customer_name_group, '');
        end if;
    end if;

    v_author_code := nullif(btrim(post.source_author_code), '');
    select display_name into account_name from user_account
     where user_account_id = post.author_account_id;
    if v_author_code is not null then
        v_author_name := case
            when nullif(btrim(post.source_author_name), '') is null
              or lower(btrim(post.source_author_name)) = lower(v_author_code)
            then null else btrim(post.source_author_name) end;
        insert into author_hint_group_read_projection values (
            post.visibility_code,
            coalesce(post.corporate_entity_id, entity_key),
            coalesce(post.process_unit_id, entity_key),
            v_author_code, post.author_account_id, account_name, v_author_name,
            greatest(delta, 0)
        ) on conflict (
            visibility_code, corporate_entity_key, process_unit_key,
            author_code, author_account_id, account_display_name
        ) do update set
            post_count = greatest(
                author_hint_group_read_projection.post_count + delta, 0
            ),
            author_name = case when delta > 0 then coalesce(greatest(
                author_hint_group_read_projection.author_name,
                excluded.author_name
            ), author_hint_group_read_projection.author_name, excluded.author_name)
            else author_hint_group_read_projection.author_name end;
        delete from author_hint_group_read_projection where post_count <= 0;
        if delta < 0 then
            update author_hint_group_read_projection grouped
               set author_name = (
                   select max(remaining.author_name)
                     from customer_master_post_read_projection remaining
                    where remaining.visibility_code = grouped.visibility_code
                      and coalesce(remaining.corporate_entity_id, entity_key) = grouped.corporate_entity_key
                      and coalesce(remaining.process_unit_id, entity_key) = grouped.process_unit_key
                      and remaining.author_code = grouped.author_code
                      and remaining.author_account_id = grouped.author_account_id
                      and remaining.account_display_name = grouped.account_display_name
               )
             where grouped.visibility_code = post.visibility_code
               and grouped.corporate_entity_key = coalesce(post.corporate_entity_id, entity_key)
               and grouped.process_unit_key = coalesce(post.process_unit_id, entity_key)
               and grouped.author_code = v_author_code
               and grouped.author_account_id = post.author_account_id
               and grouped.account_display_name = account_name;
        end if;
    end if;
    if delta > 0 and (v_customer_code is not null or v_customer_name is not null
                      or v_author_code is not null) then
        insert into customer_master_post_read_projection (
            post_id, post_title, created_at, visibility_code,
            corporate_entity_id, process_unit_id, customer_code_key,
            customer_name_group_key, customer_name, author_code, author_name,
            author_account_id, account_display_name
        ) values (
            post.post_id, post.post_title, post.created_at, post.visibility_code,
            post.corporate_entity_id, post.process_unit_id,
            coalesce(v_customer_code, ''), coalesce(v_customer_name_group, ''),
            v_customer_name, v_author_code, v_author_name,
            post.author_account_id, account_name
        ) on conflict (post_id) do update set
            post_title = excluded.post_title, created_at = excluded.created_at,
            visibility_code = excluded.visibility_code,
            corporate_entity_id = excluded.corporate_entity_id,
            process_unit_id = excluded.process_unit_id,
            customer_code_key = excluded.customer_code_key,
            customer_name_group_key = excluded.customer_name_group_key,
            customer_name = excluded.customer_name,
            author_code = excluded.author_code, author_name = excluded.author_name,
            author_account_id = excluded.author_account_id,
            account_display_name = excluded.account_display_name;
    end if;
end
$function$;

create or replace function refresh_customer_master_group_read_projection()
returns trigger language plpgsql as $function$
begin
    if tg_op <> 'INSERT' then perform customer_master_projection_apply(old, -1); end if;
    if tg_op <> 'DELETE' then perform customer_master_projection_apply(new, 1); end if;
    return null;
end
$function$;

do $migration$
begin
    if not exists (
        select 1 from pg_trigger
         where tgrelid = 'source_post'::regclass
           and tgname = 'customer_master_group_read_projection_trigger'
           and not tgisinternal
    ) then
        create trigger customer_master_group_read_projection_trigger
        after insert or update or delete on source_post
        for each row execute function refresh_customer_master_group_read_projection();
    end if;
end
$migration$;

do $backfill$
begin
if not exists (select 1 from customer_master_post_read_projection) then
insert into customer_master_post_read_projection (
    post_id, post_title, created_at, visibility_code, corporate_entity_id,
    process_unit_id, customer_code_key, customer_name_group_key, customer_name,
    author_code, author_name, author_account_id, account_display_name
)
select post.post_id, post.post_title, post.created_at, post.visibility_code,
       post.corporate_entity_id, post.process_unit_id,
       coalesce(nullif(btrim(post.source_customer_code), ''), ''),
       coalesce(case when nullif(btrim(post.source_customer_code), '') is null
                     then nullif(btrim(post.source_customer_name), '') end, ''),
       nullif(btrim(post.source_customer_name), ''),
       nullif(btrim(post.source_author_code), ''),
       case when nullif(btrim(post.source_author_name), '') is null
               or lower(btrim(post.source_author_name)) = lower(btrim(post.source_author_code))
            then null else btrim(post.source_author_name) end,
       post.author_account_id, author.display_name
  from source_post post
  join user_account author on author.user_account_id = post.author_account_id
 where (post.source_draft_code is null or btrim(post.source_draft_code) = '')
   and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')
   and (nullif(btrim(post.source_customer_code), '') is not null
        or nullif(btrim(post.source_customer_name), '') is not null
        or nullif(btrim(post.source_author_code), '') is not null);
insert into customer_hint_group_read_projection
select visibility_code,
       coalesce(corporate_entity_id, '00000000-0000-0000-0000-000000000000'),
       coalesce(process_unit_id, '00000000-0000-0000-0000-000000000000'),
       coalesce(nullif(btrim(source_customer_code), ''), ''),
       coalesce(case when nullif(btrim(source_customer_code), '') is null
                     then nullif(btrim(source_customer_name), '') end, ''),
       max(nullif(btrim(source_customer_name), '')), count(*)
  from source_post
 where (source_draft_code is null or btrim(source_draft_code) = '')
   and (source_deleted_flag is null or btrim(source_deleted_flag) = '')
   and (nullif(btrim(source_customer_code), '') is not null
        or nullif(btrim(source_customer_name), '') is not null)
 group by 1, 2, 3, 4, 5;

insert into author_hint_group_read_projection
select post.visibility_code,
       coalesce(post.corporate_entity_id, '00000000-0000-0000-0000-000000000000'),
       coalesce(post.process_unit_id, '00000000-0000-0000-0000-000000000000'),
       btrim(post.source_author_code), post.author_account_id, author.display_name,
       max(case when nullif(btrim(post.source_author_name), '') is null
                  or lower(btrim(post.source_author_name)) = lower(btrim(post.source_author_code))
                then null else btrim(post.source_author_name) end), count(*)
  from source_post post
  join user_account author on author.user_account_id = post.author_account_id
 where (post.source_draft_code is null or btrim(post.source_draft_code) = '')
   and (post.source_deleted_flag is null or btrim(post.source_deleted_flag) = '')
   and nullif(btrim(post.source_author_code), '') is not null
 group by 1, 2, 3, 4, 5, 6;
end if;
end
$backfill$;

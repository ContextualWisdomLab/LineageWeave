-- Customer-master hint lists read source fields without loading the large body
-- heap. Related-post bodies are joined only after the latest bounded rows are
-- selected.

create index if not exists source_post_customer_hint_lookup_idx
    on source_post (
        (nullif(btrim(source_customer_code), '')),
        (case
            when nullif(btrim(source_customer_code), '') is null
            then nullif(btrim(source_customer_name), '')
            else null
         end),
        created_at desc,
        post_id desc
    ) include (post_title, source_customer_name, visibility_code, corporate_entity_id)
    where nullif(btrim(source_customer_code), '') is not null
       or nullif(btrim(source_customer_name), '') is not null;

create index if not exists source_post_author_hint_lookup_idx
    on source_post (
        (btrim(source_author_code)),
        author_account_id,
        created_at desc,
        post_id desc
    ) include (post_title, source_author_name, visibility_code, corporate_entity_id)
    where source_author_code is not null
      and btrim(source_author_code) <> '';

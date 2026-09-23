-- Fail closed when a previous concurrent build left a same-named INVALID index.
-- PostgreSQL keeps failed CREATE INDEX CONCURRENTLY relations so an ordinary
-- IF NOT EXISTS replay would otherwise return success while admission still has
-- no valid access path. Recovery is the paired concurrent rollback followed by
-- this migration again.
do $$
declare
    existing_index regclass;
    index_definition text;
    index_is_valid boolean;
    index_is_ready boolean;
begin
    existing_index := to_regclass('public.global_ask_job_active_account_idx');
    if existing_index is not null then
        select index_catalog.indisvalid,
               index_catalog.indisready,
               pg_get_indexdef(index_catalog.indexrelid)
          into index_is_valid, index_is_ready, index_definition
          from pg_index index_catalog
         where index_catalog.indexrelid = existing_index;

        if coalesce(index_is_valid, false) is not true
           or coalesce(index_is_ready, false) is not true then
            raise exception
                'global_ask_job_active_account_idx is invalid; run rollback/0251_global_ask_active_admission_index.sql and retry migration 0251';
        end if;

        if lower(index_definition) like 'create unique index%'
           or index_definition not ilike '% on %global_ask_job% (requesting_account_id)%'
           or index_definition not ilike '%where%job_status_code%'
           or index_definition not ilike '%queued%'
           or index_definition not ilike '%running%' then
            raise exception
                'global_ask_job_active_account_idx exists with an incompatible definition';
        end if;
    end if;
end
$$;

create index concurrently if not exists global_ask_job_active_account_idx
    on global_ask_job (requesting_account_id)
    where job_status_code in ('queued', 'running');

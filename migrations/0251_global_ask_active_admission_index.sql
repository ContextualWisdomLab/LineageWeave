-- Serialize cooperating migration 0251 runners across the whole psql session.
-- CREATE INDEX CONCURRENTLY cannot run inside a transaction, so a transaction-
-- scoped advisory lock cannot protect the capture/preflight/create/comment chain.
-- A session lock does: concurrent LineageWeave rollout processes wait here and
-- then replay against the canonical index created by the first runner. External
-- DDL is still handled by the fail-closed duplicate-relation path below.
select pg_advisory_lock(
    hashtextextended('lineageweave:migration:0251_global_ask_active_admission_index', 0)
);

-- Capture the create/no-create decision before validation. If the name is absent
-- here and another non-cooperating session creates it later, the plain CREATE
-- below must fail; do not re-check existence with IF NOT EXISTS after preflight.
select (to_regclass('public.global_ask_job_active_account_idx') is null)
    as lineageweave_create_active_admission_index
\gset

-- Fail closed when a previous concurrent build left a same-named INVALID index.
-- PostgreSQL keeps failed CREATE INDEX CONCURRENTLY relations so an ordinary
-- replay must not report success while admission still has no valid access path.
-- Recovery is the paired concurrent rollback followed by this migration again.
-- A same-named non-index relation is a separate operator conflict and must never
-- be routed through index rollback.
do $$
declare
    existing_index regclass;
    existing_relation_kind "char";
    indexed_table regclass;
    index_definition text;
    index_predicate text;
    first_index_key text;
    index_contract text;
    index_key_count integer;
    index_attribute_count integer;
    index_is_valid boolean;
    index_is_ready boolean;
begin
    existing_index := to_regclass('public.global_ask_job_active_account_idx');
    if existing_index is not null then
        select relation_catalog.relkind
          into existing_relation_kind
          from pg_class relation_catalog
         where relation_catalog.oid = existing_index;

        if existing_relation_kind is distinct from 'i'::"char" then
            raise exception
                'global_ask_job_active_account_idx is occupied by a non-index relation or unsupported index relation kind (relkind=%); rename or remove the conflicting relation explicitly before retrying migration 0251',
                existing_relation_kind;
        end if;

        select index_catalog.indrelid,
               index_catalog.indisvalid,
               index_catalog.indisready,
               index_catalog.indnkeyatts,
               index_catalog.indnatts,
               pg_get_indexdef(index_catalog.indexrelid),
               pg_get_expr(index_catalog.indpred, index_catalog.indrelid, true),
               pg_get_indexdef(index_catalog.indexrelid, 1, true),
               obj_description(index_catalog.indexrelid, 'pg_class')
          into indexed_table,
               index_is_valid,
               index_is_ready,
               index_key_count,
               index_attribute_count,
               index_definition,
               index_predicate,
               first_index_key,
               index_contract
          from pg_index index_catalog
         where index_catalog.indexrelid = existing_index;

        if coalesce(index_is_valid, false) is not true
           or coalesce(index_is_ready, false) is not true then
            raise exception
                'global_ask_job_active_account_idx is invalid; run rollback/0251_global_ask_active_admission_index.sql and retry migration 0251';
        end if;

        if indexed_table is distinct from 'public.global_ask_job'::regclass
           or index_key_count is distinct from 1
           or index_attribute_count is distinct from 1
           or first_index_key is distinct from 'requesting_account_id'
           or index_contract is distinct from 'lineageweave/global-ask-active-admission-index/v1'
           or index_predicate is null
           or regexp_replace(lower(index_predicate), '\s+', ' ', 'g') not in (
               'job_status_code = any (array[''queued''::text, ''running''::text])',
               '(job_status_code = any (array[''queued''::text, ''running''::text]))'
           )
           or lower(index_definition) like 'create unique index%'
           or index_definition not ilike '% on %global_ask_job% (requesting_account_id)%' then
            raise exception
                'global_ask_job_active_account_idx exists with an incompatible definition';
        end if;
    end if;
end
$$;

-- Conditional DDL starts here. The decision was captured before the preflight,
-- so a relation appearing after that capture cannot turn this into a silent
-- no-op followed by an ownership COMMENT.
\if :lineageweave_create_active_admission_index
select 'create index concurrently global_ask_job_active_account_idx on public.global_ask_job (requesting_account_id) where job_status_code in (''queued'', ''running'')'
\gexec
\endif

comment on index public.global_ask_job_active_account_idx is
    'lineageweave/global-ask-active-admission-index/v1';

select pg_advisory_unlock(
    hashtextextended('lineageweave:migration:0251_global_ask_active_admission_index', 0)
);

-- Coordinate cooperating migration 0251 runners without parking a transaction
-- behind an advisory lock. CREATE INDEX CONCURRENTLY waits for old snapshots;
-- a blocking SELECT pg_advisory_lock(...) can itself own such a snapshot and
-- form a wait cycle with the index build. Use the non-blocking session lock and
-- fail fast instead. The rollout operator can retry after the active 0251
-- session exits; replay then validates the canonical index before succeeding.
select pg_try_advisory_lock(
    hashtextextended('lineageweave:migration:0251_global_ask_active_admission_index', 0)
) as lineageweave_migration_lock_acquired
\gset

\if :lineageweave_migration_lock_acquired
\else
    do $$
    begin
        raise exception 'migration 0251 is already running; retry after the active migration session exits';
    end
    $$;
\endif

-- Capture both the create/no-create decision and the exact object identity seen
-- before validation. If the name is absent here and another non-cooperating
-- session creates it later, the plain CREATE below must fail. If replay starts
-- from an existing canonical index, ownership publication must remain bound to
-- this exact OID rather than whichever relation happens to own the name later.
select to_regclass('public.global_ask_job_active_account_idx')::oid
           as lineageweave_preflight_active_admission_index_oid,
       (to_regclass('public.global_ask_job_active_account_idx') is null)
           as lineageweave_create_active_admission_index
\gset

-- Fail closed when a previous concurrent build left a same-named INVALID index.
-- PostgreSQL keeps failed CREATE INDEX CONCURRENTLY relations so an ordinary
-- replay must not report success while admission still has no valid access path.
-- Recovery is the paired concurrent rollback followed by this migration again,
-- but only after the failed relation is proven to be this migration's canonical
-- physical identity. A foreign invalid index must never inherit repository
-- rollback guidance merely because it shares the canonical name.
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
    index_access_method text;
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
               obj_description(index_catalog.indexrelid, 'pg_class'),
               access_method.amname
          into indexed_table,
               index_is_valid,
               index_is_ready,
               index_key_count,
               index_attribute_count,
               index_definition,
               index_predicate,
               first_index_key,
               index_contract,
               index_access_method
          from pg_index index_catalog
          join pg_class index_relation
            on index_relation.oid = index_catalog.indexrelid
          join pg_am access_method
            on access_method.oid = index_relation.relam
         where index_catalog.indexrelid = existing_index;

        -- Identity comes before recovery classification. Otherwise any failed
        -- concurrent index in public with this name -- including one owned by a
        -- different table or contract -- would be misreported as a repository
        -- recovery candidate even though the paired rollback correctly refuses it.
        if indexed_table is distinct from 'public.global_ask_job'::regclass
           or index_access_method is distinct from 'btree'
           or index_key_count is distinct from 1
           or index_attribute_count is distinct from 1
           or first_index_key is distinct from 'requesting_account_id'
           or index_predicate is null
           or regexp_replace(lower(index_predicate), '\s+', ' ', 'g') not in (
               'job_status_code = any (array[''queued''::text, ''running''::text])',
               '(job_status_code = any (array[''queued''::text, ''running''::text]))'
           )
           or lower(index_definition) like 'create unique index%'
           or index_definition not ilike '% on %global_ask_job% (requesting_account_id)%'
           or (
               index_contract is not null
               and index_contract is distinct from 'lineageweave/global-ask-active-admission-index/v1'
           ) then
            raise exception
                'global_ask_job_active_account_idx exists with an incompatible definition';
        end if;

        if coalesce(index_is_valid, false) is not true
           or coalesce(index_is_ready, false) is not true then
            raise exception
                'global_ask_job_active_account_idx is invalid; run rollback/0251_global_ask_active_admission_index.sql and retry migration 0251';
        end if;

        if index_contract is distinct from 'lineageweave/global-ask-active-admission-index/v1' then
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
select 'public.global_ask_job_active_account_idx'::regclass::oid
    as lineageweave_expected_active_admission_index_oid
\gset
\else
select :'lineageweave_preflight_active_admission_index_oid'::oid
    as lineageweave_expected_active_admission_index_oid
\gset
\endif

-- Bind the final ownership decision to the same PostgreSQL object that was
-- validated or created above. SHARE UPDATE EXCLUSIVE still admits ordinary DML
-- (ROW EXCLUSIVE) while excluding index/schema churn on global_ask_job during
-- the short publication transaction. If a privileged non-cooperating session
-- swapped the named index before this lock was acquired, the OID check fails
-- closed before any repository ownership marker can be written.
begin;
lock table public.global_ask_job in share update exclusive mode;

select coalesce(
           to_regclass('public.global_ask_job_active_account_idx')::oid =
               :'lineageweave_expected_active_admission_index_oid'::oid,
           false
       ) as lineageweave_active_admission_index_identity_preserved
\gset

\if :lineageweave_active_admission_index_identity_preserved
\else
    do $$
    begin
        raise exception
            'global_ask_job_active_account_idx changed after migration 0251 preflight; retry after resolving concurrent DDL';
    end
    $$;
\endif

\if :lineageweave_create_active_admission_index
comment on index public.global_ask_job_active_account_idx is
    'lineageweave/global-ask-active-admission-index/v1';
\else
select coalesce(
           obj_description(
               'public.global_ask_job_active_account_idx'::regclass,
               'pg_class'
           ) = 'lineageweave/global-ask-active-admission-index/v1',
           false
       ) as lineageweave_existing_active_admission_contract_preserved
\gset

\if :lineageweave_existing_active_admission_contract_preserved
\else
    do $$
    begin
        raise exception
            'global_ask_job_active_account_idx ownership marker changed after migration 0251 preflight';
    end
    $$;
\endif
\endif

commit;

select pg_advisory_unlock(
    hashtextextended('lineageweave:migration:0251_global_ask_active_admission_index', 0)
);

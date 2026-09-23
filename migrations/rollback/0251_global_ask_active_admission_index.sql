-- Destructive rollback must validate and delete the same relation identity. Keep
-- the parent table exclusively locked for the short rollback transaction so a
-- concurrent session cannot replace the validated index before DROP executes.
-- Fail immediately when that lock is unavailable: operators can drain the busy
-- path and retry instead of leaving a destructive recovery session waiting on
-- production traffic. This deliberately favors destructive-action safety over
-- concurrent writes; the normal forward path remains CREATE INDEX CONCURRENTLY.
begin;

lock table public.global_ask_job in access exclusive mode nowait;

-- Fail closed before destructive rollback. A valid same-named index without the
-- repository ownership marker may be operator-owned even when its physical
-- definition happens to match this migration. The only unmarked object this
-- rollback may remove automatically is an incomplete canonical-shaped index
-- left by a failed CREATE INDEX CONCURRENTLY attempt.
do $$
declare
    existing_index regclass;
    existing_relation_kind "char";
    indexed_table regclass;
    index_predicate text;
    first_index_key text;
    index_contract text;
    index_access_method text;
    index_key_count integer;
    index_attribute_count integer;
    index_is_valid boolean;
    index_is_ready boolean;
    index_is_unique boolean;
begin
    existing_index := to_regclass('public.global_ask_job_active_account_idx');
    if existing_index is null then
        return;
    end if;

    select relation_catalog.relkind
      into existing_relation_kind
      from pg_class relation_catalog
     where relation_catalog.oid = existing_index;

    if existing_relation_kind is distinct from 'i'::"char" then
        raise exception
            'refusing rollback: public.global_ask_job_active_account_idx is not an ordinary index (relkind=%); resolve the conflicting relation explicitly',
            existing_relation_kind;
    end if;

    select index_catalog.indrelid,
           index_catalog.indisvalid,
           index_catalog.indisready,
           index_catalog.indisunique,
           index_catalog.indnkeyatts,
           index_catalog.indnatts,
           pg_get_expr(index_catalog.indpred, index_catalog.indrelid, true),
           pg_get_indexdef(index_catalog.indexrelid, 1, true),
           obj_description(index_catalog.indexrelid, 'pg_class'),
           access_method.amname
      into indexed_table,
           index_is_valid,
           index_is_ready,
           index_is_unique,
           index_key_count,
           index_attribute_count,
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

    if indexed_table is distinct from 'public.global_ask_job'::regclass
       or index_access_method is distinct from 'btree'
       or coalesce(index_is_unique, false) is true
       or index_key_count is distinct from 1
       or index_attribute_count is distinct from 1
       or first_index_key is distinct from 'requesting_account_id'
       or index_predicate is null
       or regexp_replace(lower(index_predicate), '\s+', ' ', 'g') not in (
           'job_status_code = any (array[''queued''::text, ''running''::text])',
           '(job_status_code = any (array[''queued''::text, ''running''::text]))'
       ) then
        raise exception
            'refusing rollback: public.global_ask_job_active_account_idx has an incompatible physical definition; resolve ownership explicitly';
    end if;

    if index_contract is not null
       and index_contract is distinct from 'lineageweave/global-ask-active-admission-index/v1' then
        raise exception
            'refusing rollback: public.global_ask_job_active_account_idx carries an unexpected ownership marker; resolve ownership explicitly';
    end if;

    if coalesce(index_is_valid, false) is true
       and coalesce(index_is_ready, false) is true
       and index_contract is distinct from 'lineageweave/global-ask-active-admission-index/v1' then
        raise exception
            'refusing rollback: public.global_ask_job_active_account_idx is valid but not repository-owned; resolve ownership explicitly';
    end if;
end
$$;

drop index if exists public.global_ask_job_active_account_idx;

commit;

begin;

-- ADR 0008: only search-corroborated raw/canonical pairs act as Global Ask
-- aliases. These column indexes preserve multilingual contains-search without
-- copying context-scoped labels into a second table.
create extension if not exists pg_trgm;

create index if not exists organization_name_resolution_raw_search_idx
    on organization_name_resolution using gin (raw_organization_name gin_trgm_ops);
create index if not exists organization_name_resolution_resolved_search_idx
    on organization_name_resolution using gin (resolved_organization_name gin_trgm_ops);

commit;

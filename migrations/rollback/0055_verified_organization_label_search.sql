begin;

drop index if exists organization_name_resolution_resolved_search_idx;
drop index if exists organization_name_resolution_raw_search_idx;

-- pg_trgm is shared with the broader Global Ask search slice.
commit;

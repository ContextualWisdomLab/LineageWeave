-- ADR 0033: persist Searxng abbreviation matches against the existing
-- customer-group tree. CREATE IF NOT EXISTS so a volume that already
-- ran 0001 still upgrades. Does not invent a parent or insert a
-- corporate_entity row.

create table if not exists abbreviation_tree_corroboration (
    abbreviation_tree_corroboration_id uuid primary key default uuid_generate_v4(),
    raw_organization_name text not null unique,
    corporate_entity_id uuid references corporate_entity (corporate_entity_id),
    verification_status_code text not null references common_lookup_value (lookup_code),
    verification_evidence_url text,
    corroborated_at timestamptz not null default now()
);

create index if not exists abbreviation_tree_corroboration_entity_idx
    on abbreviation_tree_corroboration (corporate_entity_id)
    where corporate_entity_id is not null;

comment on table abbreviation_tree_corroboration is
    'Caches Searxng corroboration of a raw organization mention against an existing customer-group tree node. Fail-closed: no parent and no AUTO row when search is down, empty, or tied.';

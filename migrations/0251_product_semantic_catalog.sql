-- ADR 0228: evidence-bound product identity and operational relationships.
create table if not exists product_catalog (
    product_catalog_id uuid primary key default gen_random_uuid(),
    canonical_product_name text not null check (btrim(canonical_product_name) <> ''),
    product_level_code text not null
        check (product_level_code in ('product_group', 'product_model', 'variant', 'trade_item')),
    parent_product_catalog_id uuid references product_catalog(product_catalog_id),
    product_catalog_code text,
    created_at timestamptz not null default now(),
    unique (product_catalog_code)
);

create table if not exists product_catalog_identifier (
    product_catalog_id uuid not null references product_catalog(product_catalog_id),
    identifier_scheme_code text not null check (identifier_scheme_code in ('gtin', 'mpn')),
    identifier_value text not null check (btrim(identifier_value) <> ''),
    issuer_scope_text text not null check (btrim(issuer_scope_text) <> ''),
    primary key (identifier_scheme_code, identifier_value, issuer_scope_text),
    unique (product_catalog_id, identifier_scheme_code, identifier_value, issuer_scope_text)
);

create table if not exists product_catalog_alias (
    product_catalog_id uuid not null references product_catalog(product_catalog_id),
    normalized_alias_text text not null check (btrim(normalized_alias_text) <> ''),
    alias_text text not null check (btrim(alias_text) <> ''),
    primary key (product_catalog_id, normalized_alias_text)
);
create index if not exists product_catalog_alias_lookup_idx
    on product_catalog_alias (normalized_alias_text, product_catalog_id);

create table if not exists post_product_analysis (
    post_id uuid primary key references source_post(post_id) on delete cascade,
    source_body_sha256 text not null check (source_body_sha256 ~ '^[0-9a-f]{64}$'),
    analysis_input_sha256 text not null check (analysis_input_sha256 ~ '^[0-9a-f]{64}$'),
    orchestrator_session_id text not null check (btrim(orchestrator_session_id) <> ''),
    analyzed_at timestamptz not null default now()
);

create table if not exists post_product_mention (
    post_id uuid not null references post_product_analysis(post_id) on delete cascade,
    mention_ordinal integer not null check (mention_ordinal >= 0),
    product_catalog_id uuid references product_catalog(product_catalog_id),
    extracted_product_name text not null check (btrim(extracted_product_name) <> ''),
    resolution_status_code text not null
        check (resolution_status_code in ('unique', 'missing', 'tie', 'unavailable')),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    evidence_post_id uuid not null references source_post(post_id),
    evidence_input_sha256 text not null
        check (evidence_input_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (post_id, mention_ordinal),
    check ((resolution_status_code = 'unique') = (product_catalog_id is not null))
);
create index if not exists post_product_mention_catalog_idx
    on post_product_mention (product_catalog_id, post_id)
    where product_catalog_id is not null;

create table if not exists product_operations_fact_relation (
    post_id uuid not null,
    mention_ordinal integer not null,
    case_kind_code text not null,
    fact_ordinal integer not null,
    relation_type_code text not null
        check (relation_type_code in ('concerns_product', 'changes_product', 'originates_from_product', 'senses_product')),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    evidence_post_id uuid not null references source_post(post_id),
    evidence_input_sha256 text not null
        check (evidence_input_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (post_id, mention_ordinal, case_kind_code, fact_ordinal, relation_type_code),
    foreign key (post_id, mention_ordinal)
        references post_product_mention(post_id, mention_ordinal) on delete cascade,
    foreign key (post_id, case_kind_code, fact_ordinal)
        references operations_case_fact(post_id, case_kind_code, fact_ordinal) on delete cascade
);

create table if not exists product_project_relation (
    post_id uuid not null,
    mention_ordinal integer not null,
    project_key text not null,
    relation_type_code text not null check (relation_type_code = 'used_by_project'),
    evidence_text text not null check (btrim(evidence_text) <> ''),
    evidence_post_id uuid not null references source_post(post_id),
    evidence_input_sha256 text not null
        check (evidence_input_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (post_id, mention_ordinal, project_key),
    foreign key (post_id, mention_ordinal)
        references post_product_mention(post_id, mention_ordinal) on delete cascade,
    foreign key (post_id, project_key)
        references post_project_mention(post_id, project_key) on delete cascade
);

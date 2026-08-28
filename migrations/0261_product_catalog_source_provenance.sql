-- ADR 0228: explicit governed source provenance for product-catalog entries.
create table if not exists product_catalog_source_record (
    corporate_entity_id uuid not null references corporate_entity(corporate_entity_id),
    source_system_code text not null check (source_system_code ~ '^[a-z][a-z0-9_]{0,62}$'),
    source_record_key text not null check (btrim(source_record_key) <> ''),
    product_catalog_id uuid not null references product_catalog(product_catalog_id),
    source_payload_sha256 text not null check (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    preferred_label_text text not null check (btrim(preferred_label_text) <> ''),
    imported_by_account_id uuid not null references user_account(user_account_id),
    imported_at timestamptz not null default clock_timestamp(),
    primary key (corporate_entity_id, source_system_code, source_record_key)
);

create index if not exists product_catalog_source_record_product_idx
    on product_catalog_source_record
       (product_catalog_id, corporate_entity_id, source_system_code, source_record_key);

create table if not exists product_catalog_alias_source (
    product_catalog_id uuid not null,
    normalized_alias_text text not null,
    source_alias_text text not null check (btrim(source_alias_text) <> ''),
    corporate_entity_id uuid not null,
    source_system_code text not null,
    source_record_key text not null,
    primary key (
        product_catalog_id, normalized_alias_text,
        corporate_entity_id, source_system_code, source_record_key
    ),
    foreign key (product_catalog_id, normalized_alias_text)
        references product_catalog_alias(product_catalog_id, normalized_alias_text)
        on delete cascade,
    foreign key (corporate_entity_id, source_system_code, source_record_key)
        references product_catalog_source_record(
            corporate_entity_id, source_system_code, source_record_key
        ) on delete restrict
);

create index if not exists product_catalog_alias_source_record_idx
    on product_catalog_alias_source
       (corporate_entity_id, source_system_code, source_record_key, product_catalog_id);

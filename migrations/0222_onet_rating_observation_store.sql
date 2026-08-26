-- ADR 0254: normalized, immutable O*NET occupation-rating source evidence.
-- Release and source-table LIST partitions are created by the importer before
-- data insertion; no default partition may silently absorb an unknown source.

begin;

create table if not exists occupational_data_release (
    data_release_code text primary key,
    release_version text not null,
    source_publisher_name text not null,
    source_license_url text not null,
    imported_at timestamptz not null default now(),
    constraint occupational_data_release_code_check
        check (btrim(data_release_code) <> ''),
    constraint occupational_release_version_check
        check (btrim(release_version) <> '')
);

create table if not exists occupational_source_table (
    data_release_code text not null,
    source_table_code text not null,
    source_table_name text not null,
    source_artifact_url text not null,
    source_artifact_sha256 text not null,
    source_row_count bigint not null,
    primary key (data_release_code, source_table_code),
    constraint occupational_source_table_release_fkey
        foreign key (data_release_code)
        references occupational_data_release (data_release_code),
    constraint occupational_source_table_code_check
        check (btrim(source_table_code) <> ''),
    constraint occupational_source_artifact_check
        check (source_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    constraint occupational_source_row_count_check
        check (source_row_count > 0)
);

create table if not exists occupational_scale_definition (
    data_release_code text not null,
    scale_id text not null,
    scale_name text not null,
    minimum_value numeric not null,
    maximum_value numeric not null,
    primary key (data_release_code, scale_id),
    constraint occupational_scale_release_fkey
        foreign key (data_release_code)
        references occupational_data_release (data_release_code),
    constraint occupational_scale_id_check check (btrim(scale_id) <> ''),
    constraint occupational_scale_bounds_check
        check (minimum_value <= maximum_value)
);

create table if not exists occupational_classification_entry (
    data_release_code text not null,
    onetsoc_code text not null,
    occupation_title text not null,
    primary key (data_release_code, onetsoc_code),
    constraint occupational_classification_release_fkey
        foreign key (data_release_code)
        references occupational_data_release (data_release_code),
    constraint occupational_onetsoc_code_check
        check (onetsoc_code ~ '^[0-9]{2}-[0-9]{4}\.[0-9]{2}$'),
    constraint occupational_title_check check (btrim(occupation_title) <> '')
);

create table if not exists occupational_element_definition (
    data_release_code text not null,
    element_id text not null,
    element_name text not null,
    primary key (data_release_code, element_id),
    constraint occupational_element_release_fkey
        foreign key (data_release_code)
        references occupational_data_release (data_release_code),
    constraint occupational_element_id_check
        check (element_id ~ '^[1-6](\.[A-Za-z0-9]+)*$'),
    constraint occupational_element_name_check check (btrim(element_name) <> '')
);

create table if not exists occupational_rating_observation (
    data_release_code text not null,
    source_table_code text not null,
    onetsoc_code text not null,
    element_id text not null,
    scale_id text not null,
    category_value integer,
    data_value numeric not null,
    sample_size integer,
    standard_error numeric,
    lower_ci_bound numeric,
    upper_ci_bound numeric,
    recommend_suppress boolean,
    not_relevant boolean,
    source_updated_date date not null,
    domain_source_code text not null,
    constraint occupational_rating_source_table_fkey
        foreign key (data_release_code, source_table_code)
        references occupational_source_table (data_release_code, source_table_code),
    constraint occupational_rating_classification_fkey
        foreign key (data_release_code, onetsoc_code)
        references occupational_classification_entry (data_release_code, onetsoc_code),
    constraint occupational_rating_element_fkey
        foreign key (data_release_code, element_id)
        references occupational_element_definition (data_release_code, element_id),
    constraint occupational_rating_scale_fkey
        foreign key (data_release_code, scale_id)
        references occupational_scale_definition (data_release_code, scale_id),
    constraint occupational_rating_identity_key
        unique nulls not distinct
        (data_release_code, source_table_code, onetsoc_code, element_id, scale_id, category_value),
    constraint occupational_rating_sample_size_check
        check (sample_size is null or sample_size > 0),
    constraint occupational_rating_standard_error_check
        check (standard_error is null or standard_error >= 0),
    constraint occupational_rating_interval_presence_check
        check ((lower_ci_bound is null) = (upper_ci_bound is null)),
    constraint occupational_rating_interval_order_check
        check (lower_ci_bound is null or lower_ci_bound <= upper_ci_bound),
    constraint occupational_rating_data_value_check
        check (data_value::text not in ('NaN', 'Infinity', '-Infinity')),
    constraint occupational_rating_domain_source_check
        check (btrim(domain_source_code) <> '')
) partition by list (data_release_code);

create index if not exists occupational_rating_occupation_element_idx
    on occupational_rating_observation
    (data_release_code, onetsoc_code, element_id, scale_id);

create index if not exists occupational_rating_element_occupation_idx
    on occupational_rating_observation
    (data_release_code, element_id, scale_id, onetsoc_code);

commit;

-- ADR 0091: visual-region descriptions are independently searchable units.
create table if not exists post_content_image_region_embedding (
    post_content_image_region_embedding_id uuid primary key default gen_random_uuid(),
    post_content_image_region_id uuid not null
        references post_content_image_region(post_content_image_region_id) on delete cascade,
    embedding_model_code text not null,
    embedding_dimension_count integer not null check (embedding_dimension_count > 0),
    created_at timestamptz not null default now(),
    unique (post_content_image_region_id, embedding_model_code)
);

create table if not exists post_content_image_region_embedding_value (
    post_content_image_region_embedding_id uuid not null
        references post_content_image_region_embedding(post_content_image_region_embedding_id)
        on delete cascade,
    dimension_index integer not null check (dimension_index >= 0),
    dimension_value double precision not null,
    primary key (post_content_image_region_embedding_id, dimension_index)
);

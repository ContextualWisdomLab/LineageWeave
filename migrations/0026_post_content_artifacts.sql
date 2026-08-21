begin;

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('post_content_unit_kind', 'plain_text', 'Plain text', 0),
    ('post_content_unit_kind', 'dom', 'DOM block', 1),
    ('post_content_unit_kind', 'image', 'Embedded image', 2),
    ('post_content_image_status', 'described', 'Described by vision model', 0),
    ('post_content_image_status', 'unavailable', 'Vision channel unavailable', 1),
    ('post_content_image_status', 'failed', 'Vision request failed', 2)
on conflict (lookup_code) do nothing;

create table if not exists post_content_unit (
    post_content_unit_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post(post_id) on delete cascade,
    unit_index integer not null check (unit_index >= 0),
    unit_kind_code text not null references common_lookup_value(lookup_code),
    unit_label text not null default '',
    unit_text text not null,
    inline_style text,
    created_at timestamptz not null default now(),
    unique (post_id, unit_index)
);

create index if not exists post_content_unit_post_idx
    on post_content_unit (post_id, unit_index);

create table if not exists post_content_image (
    post_content_image_id uuid primary key default gen_random_uuid(),
    post_content_unit_id uuid not null unique references post_content_unit(post_content_unit_id) on delete cascade,
    mime_type text not null,
    content_sha256 text not null,
    byte_length integer not null check (byte_length >= 0),
    description_status_code text not null references common_lookup_value(lookup_code),
    extracted_text text,
    caption text,
    created_at timestamptz not null default now()
);

create index if not exists post_content_image_sha_idx
    on post_content_image (content_sha256);

create table if not exists post_content_image_tag (
    post_content_image_id uuid not null references post_content_image(post_content_image_id) on delete cascade,
    tag_text text not null,
    primary key (post_content_image_id, tag_text)
);

create table if not exists post_content_embedding (
    post_content_embedding_id uuid primary key default gen_random_uuid(),
    post_content_unit_id uuid not null references post_content_unit(post_content_unit_id) on delete cascade,
    embedding_model_code text not null,
    embedding_dimension_count integer not null check (embedding_dimension_count > 0),
    created_at timestamptz not null default now(),
    unique (post_content_unit_id, embedding_model_code)
);

create table if not exists post_content_embedding_value (
    post_content_embedding_id uuid not null references post_content_embedding(post_content_embedding_id) on delete cascade,
    dimension_index integer not null check (dimension_index >= 0),
    dimension_value double precision not null,
    primary key (post_content_embedding_id, dimension_index)
);

commit;

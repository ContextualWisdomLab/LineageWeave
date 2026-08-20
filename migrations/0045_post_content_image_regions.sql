-- ADR 0067: persist visual regions below the DOM image unit.
insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values ('post_content_image_region_status', 'described', 'Described visual region', 0),
       ('post_content_image_region_status', 'failed', 'Visual region description failed', 1)
on conflict (lookup_code) do nothing;

create table if not exists post_content_image_region (
    post_content_image_region_id uuid primary key default gen_random_uuid(),
    post_content_image_id uuid not null references post_content_image(post_content_image_id) on delete cascade,
    region_index integer not null check (region_index >= 0),
    x_ratio double precision not null check (x_ratio >= 0 and x_ratio <= 1),
    y_ratio double precision not null check (y_ratio >= 0 and y_ratio <= 1),
    width_ratio double precision not null check (width_ratio > 0 and width_ratio <= 1),
    height_ratio double precision not null check (height_ratio > 0 and height_ratio <= 1),
    description_status_code text not null references common_lookup_value(lookup_code),
    extracted_text text,
    caption text,
    created_at timestamptz not null default now(),
    unique (post_content_image_id, region_index),
    check (x_ratio + width_ratio <= 1),
    check (y_ratio + height_ratio <= 1)
);

create table if not exists post_content_image_region_tag (
    post_content_image_region_id uuid not null references post_content_image_region(post_content_image_region_id) on delete cascade,
    tag_text text not null,
    primary key (post_content_image_region_id, tag_text)
);

begin;

create extension if not exists pgcrypto;

create table if not exists post_content_embedding_exact_projection_state (
    singleton boolean primary key default true check (singleton),
    projection_version bigint not null check (projection_version >= 0),
    changed_at timestamptz not null default now()
);

insert into post_content_embedding_exact_projection_state
    (singleton, projection_version)
values (true, 0)
on conflict (singleton) do nothing;

create table if not exists post_content_embedding_exact_projection (
    post_content_embedding_id uuid primary key references post_content_embedding(post_content_embedding_id) on delete cascade,
    post_content_unit_id uuid not null references post_content_unit(post_content_unit_id) on delete cascade,
    post_id uuid not null references source_post(post_id) on delete cascade,
    unit_index integer not null check (unit_index >= 0),
    embedding_model_code text not null,
    embedding_dimension_count integer not null check (embedding_dimension_count > 0),
    vector_bytes bytea not null,
    vector_sha256 text not null check (vector_sha256 ~ '^[0-9a-f]{64}$'),
    projected_at timestamptz not null default now(),
    check (octet_length(vector_bytes) = embedding_dimension_count * 8)
);

create index if not exists post_content_embedding_exact_projection_snapshot_idx
    on post_content_embedding_exact_projection
       (embedding_model_code, embedding_dimension_count, post_id,
        post_content_unit_id);

create or replace function bump_post_content_embedding_exact_projection_version()
returns trigger
language plpgsql
as $$
begin
    update post_content_embedding_exact_projection_state
       set projection_version = projection_version + 1,
           changed_at = now()
     where singleton;
    return null;
end;
$$;

drop trigger if exists post_content_embedding_exact_projection_version
    on post_content_embedding_exact_projection;
create trigger post_content_embedding_exact_projection_version
after insert or update or delete on post_content_embedding_exact_projection
for each statement execute function bump_post_content_embedding_exact_projection_version();

create or replace function refresh_post_content_embedding_exact_projection(
    requested_embedding_ids uuid[]
)
returns bigint
language plpgsql
as $$
begin
    if requested_embedding_ids is null or cardinality(requested_embedding_ids) = 0 then
        return (
            select projection_version
              from post_content_embedding_exact_projection_state
             where singleton
        );
    end if;

    delete from post_content_embedding_exact_projection projection
     where projection.post_content_embedding_id = any(requested_embedding_ids);

    insert into post_content_embedding_exact_projection (
        post_content_embedding_id,
        post_content_unit_id,
        post_id,
        unit_index,
        embedding_model_code,
        embedding_dimension_count,
        vector_bytes,
        vector_sha256,
        projected_at
    )
    select embedding.post_content_embedding_id,
           unit.post_content_unit_id,
           unit.post_id,
           unit.unit_index,
           embedding.embedding_model_code,
           embedding.embedding_dimension_count,
           packed.vector_bytes,
           encode(digest(packed.vector_bytes, 'sha256'), 'hex'),
           now()
      from post_content_embedding embedding
      join post_content_unit unit
        on unit.post_content_unit_id = embedding.post_content_unit_id
      join lateral (
          select string_agg(
                     float8send(value.dimension_value),
                     ''::bytea
                     order by value.dimension_index
                 ) as vector_bytes,
                 count(*) as dimension_count,
                 min(value.dimension_index) as minimum_dimension,
                 max(value.dimension_index) as maximum_dimension
            from post_content_embedding_value value
           where value.post_content_embedding_id = embedding.post_content_embedding_id
      ) packed on true
     where embedding.post_content_embedding_id = any(requested_embedding_ids)
       and packed.dimension_count = embedding.embedding_dimension_count
       and packed.minimum_dimension = 0
       and packed.maximum_dimension = embedding.embedding_dimension_count - 1;

    return (
        select projection_version
          from post_content_embedding_exact_projection_state
         where singleton
    );
end;
$$;

do $$
begin
    if not exists (
        select 1 from post_content_embedding_exact_projection
    ) then
        perform refresh_post_content_embedding_exact_projection(
            array(
                select post_content_embedding_id
                  from post_content_embedding
                 order by post_content_embedding_id
            )
        );
    end if;
end;
$$;

commit;

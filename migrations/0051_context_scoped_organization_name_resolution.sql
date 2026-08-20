-- ADR 0008: the same short organization name may resolve differently in
-- different post contexts. Keep only a digest of the context, never the body.
alter table organization_name_resolution
    add column if not exists context_sha256 text;

update organization_name_resolution
   set context_sha256 = ''
 where context_sha256 is null;

alter table organization_name_resolution
    alter column context_sha256 set default '',
    alter column context_sha256 set not null;

alter table organization_name_resolution
    drop constraint if exists organization_name_resolution_pkey;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'organization_name_resolution_context_pkey'
    ) then
        alter table organization_name_resolution
            add constraint organization_name_resolution_context_pkey
            primary key (raw_organization_name, context_sha256);
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'organization_name_resolution_context_sha256_check'
    ) then
        alter table organization_name_resolution
            add constraint organization_name_resolution_context_sha256_check
            check (
                context_sha256 = ''
                or context_sha256 ~ '^[0-9a-f]{64}$'
            );
    end if;
end
$$;

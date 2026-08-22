begin;

alter table tenant_settings
    add column if not exists system_name text not null default 'LineageWeave',
    add column if not exists copyright_year integer not null default 2026,
    add column if not exists copyright_holder text not null default 'LineageWeave';

-- Repair values written by the legacy brand-only endpoint before validating
-- the new contract. Non-empty tenant-owned values remain unchanged.
update public.tenant_settings
   set brand_name = case
                        when nullif(btrim(brand_name), '') is null then 'LineageWeave'
                        else brand_name
                    end,
       system_name = case
                         when nullif(btrim(system_name), '') is null then 'LineageWeave'
                         else system_name
                     end,
       copyright_year = case
                           when copyright_year is null or copyright_year not between 1900 and 2100
                               then 2026
                           else copyright_year
                       end,
       copyright_holder = case
                              when nullif(btrim(copyright_holder), '') is null then 'LineageWeave'
                              else copyright_holder
                          end
 where nullif(btrim(brand_name), '') is null
    or nullif(btrim(system_name), '') is null
    or copyright_year is null
    or copyright_year not between 1900 and 2100
    or nullif(btrim(copyright_holder), '') is null;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.tenant_settings'::regclass
           and conname = 'tenant_settings_brand_name_nonempty_check'
    ) then
        alter table public.tenant_settings
            add constraint tenant_settings_brand_name_nonempty_check
            check (nullif(btrim(brand_name), '') is not null);
    end if;
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.tenant_settings'::regclass
           and conname = 'tenant_settings_system_name_nonempty_check'
    ) then
        alter table public.tenant_settings
            add constraint tenant_settings_system_name_nonempty_check
            check (nullif(btrim(system_name), '') is not null);
    end if;
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.tenant_settings'::regclass
           and conname = 'tenant_settings_copyright_year_range_check'
    ) then
        alter table public.tenant_settings
            add constraint tenant_settings_copyright_year_range_check
            check (copyright_year between 1900 and 2100);
    end if;
    if not exists (
        select 1
          from pg_constraint
         where conrelid = 'public.tenant_settings'::regclass
           and conname = 'tenant_settings_copyright_holder_nonempty_check'
    ) then
        alter table public.tenant_settings
            add constraint tenant_settings_copyright_holder_nonempty_check
            check (nullif(btrim(copyright_holder), '') is not null);
    end if;
end
$$;

comment on column tenant_settings.system_name is
    'Configured web-system name shown beside the tenant brand identity.';
comment on column tenant_settings.copyright_year is
    'Approved major-open copyright year, not the browser current year.';
comment on column tenant_settings.copyright_holder is
    'Approved copyright rights holder shown in the footer.';

commit;

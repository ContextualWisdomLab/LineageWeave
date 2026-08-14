-- Roles & responsibilities' named actor is not always a person --
-- business correspondence routinely names an organization acting in its
-- own name ("당사" [our company], "Demo Corp"), not an
-- individual. Adds a PROV-O-grounded person/organization distinction
-- (see ADR 0006) plus an inferred affiliated-organization name for
-- person actors. The rename below (person_name -> actor_name) preserves
-- every existing row's data -- a plain RENAME COLUMN, not a drop/recreate
-- -- since a volume that already ran the pre-0006 0001 has real rows
-- under the old name.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('prov_agent_type', 'prov_person', 'Person', 0),
    ('prov_agent_type', 'prov_organization', 'Organization', 1)
on conflict (lookup_code) do nothing;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_summary_role'
          and column_name = 'person_name'
    ) then
        alter table post_summary_role rename column person_name to actor_name;
    end if;
end $$;

alter table post_summary_role
    add column if not exists actor_type_code text not null default 'prov_person'
        references common_lookup_value (lookup_code);

alter table post_summary_role
    add column if not exists affiliated_organization_name text;

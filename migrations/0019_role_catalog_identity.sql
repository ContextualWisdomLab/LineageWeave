-- ADR 0019: persist the catalog identity resolved for an R&R actor.
-- Fetching by corporate_entity.entity_name is not identifying -- two
-- companies can share a display name, and two same-named mentions on
-- one post can then attach the wrong catalog id or duplicate the role.

alter table post_summary_role
    add column if not exists cataloged_team_id uuid
        references cataloged_team (team_id),
    add column if not exists corporate_entity_id uuid
        references corporate_entity (corporate_entity_id),
    add column if not exists cataloged_person_id uuid
        references cataloged_person (person_id);

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_summary_role_one_catalog_chk'
    ) then
        alter table post_summary_role
            add constraint post_summary_role_one_catalog_chk check (
                (cataloged_team_id is not null)::int
                + (corporate_entity_id is not null)::int
                + (cataloged_person_id is not null)::int
                <= 1
            );
    end if;
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_summary_role_catalog_type_chk'
    ) then
        alter table post_summary_role
            add constraint post_summary_role_catalog_type_chk check (
                (cataloged_team_id is null or actor_type_code = 'prov_team')
                and (
                    corporate_entity_id is null
                    or actor_type_code = 'prov_organization'
                )
                and (
                    cataloged_person_id is null
                    or actor_type_code = 'prov_person'
                )
            );
    end if;
end
$$;

update post_summary_role role
   set cataloged_team_id = team.team_id
  from cataloged_team team
  join post_team_mention mention
    on mention.team_id = team.team_id
   and mention.post_id = role.post_id
 where role.actor_type_code = 'prov_team'
   and role.cataloged_team_id is null
   and team.team_name = role.actor_name
   and team.affiliated_organization_name
       is not distinct from role.affiliated_organization_name;

update post_summary_role role
   set corporate_entity_id = picked.corporate_entity_id
  from (
        select distinct on (role_key.post_id, role_key.actor_name)
               role_key.post_id,
               role_key.actor_name,
               org.corporate_entity_id
          from post_summary_role role_key
          join post_organization_mention mention
            on mention.post_id = role_key.post_id
          join corporate_entity org
            on org.corporate_entity_id = mention.corporate_entity_id
           and org.entity_name = role_key.actor_name
         where role_key.actor_type_code = 'prov_organization'
           and role_key.corporate_entity_id is null
         order by role_key.post_id, role_key.actor_name, org.corporate_entity_id
  ) picked
 where role.post_id = picked.post_id
   and role.actor_name = picked.actor_name
   and role.actor_type_code = 'prov_organization'
   and role.corporate_entity_id is null;

update post_summary_role role
   set cataloged_person_id = picked.person_id
  from (
        select distinct on (role_key.post_id, role_key.actor_name)
               role_key.post_id,
               role_key.actor_name,
               person.person_id
          from post_summary_role role_key
          join post_summary_person_mention mention
            on mention.post_id = role_key.post_id
          join cataloged_person person
            on person.person_id = mention.person_id
           and person.person_name = role_key.actor_name
         where role_key.actor_type_code = 'prov_person'
           and role_key.cataloged_person_id is null
         order by role_key.post_id,
                  role_key.actor_name,
                  person.created_at,
                  person.person_id
  ) picked
 where role.post_id = picked.post_id
   and role.actor_name = picked.actor_name
   and role.actor_type_code = 'prov_person'
   and role.cataloged_person_id is null;

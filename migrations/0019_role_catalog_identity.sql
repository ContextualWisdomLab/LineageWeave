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

-- Organizations: copy a mention only when exactly one mentioned org on
-- that post has this role's actor_name. Two same-named mentions stay
-- unbound rather than guessing a UUID (Fellegi & Sunter, 1969).
update post_summary_role role
   set corporate_entity_id = matched.corporate_entity_id
  from (
        select mention.post_id,
               org.entity_name,
               min(org.corporate_entity_id) as corporate_entity_id
          from post_organization_mention mention
          join corporate_entity org
            on org.corporate_entity_id = mention.corporate_entity_id
         group by mention.post_id, org.entity_name
        having count(*) = 1
  ) matched
 where role.actor_type_code = 'prov_organization'
   and role.corporate_entity_id is null
   and role.post_id = matched.post_id
   and role.actor_name = matched.entity_name;

-- People: the same honesty rule. Write-time persist still orders by
-- created_at, then person_id. Historical backfill must not invent a
-- binding when two same-named mentions already exist on the post.
update post_summary_role role
   set cataloged_person_id = matched.person_id
  from (
        select mention.post_id,
               person.person_name,
               min(person.person_id) as person_id
          from post_summary_person_mention mention
          join cataloged_person person
            on person.person_id = mention.person_id
         group by mention.post_id, person.person_name
        having count(*) = 1
  ) matched
 where role.actor_type_code = 'prov_person'
   and role.cataloged_person_id is null
   and role.post_id = matched.post_id
   and role.actor_name = matched.person_name;

-- ADR 0019: bind each R&R role to the catalog row resolved for that
-- role. corporate_entity.entity_name is not unique, so a fetch join on
-- name can attach a homonym or duplicate the role. Mention tables are
-- post-scoped, not role-scoped, and cannot reconstruct that binding.

alter table post_summary_role
    add column if not exists cataloged_team_id uuid
        references cataloged_team (team_id);

alter table post_summary_role
    add column if not exists cataloged_corporate_entity_id uuid
        references corporate_entity (corporate_entity_id);

-- Teams already have a unique (team_name, affiliated_organization_name)
-- key. Backfill only when that pair was mentioned on the same post.
update post_summary_role as role
   set cataloged_team_id = team.team_id
  from cataloged_team as team
  join post_team_mention as mention
    on mention.team_id = team.team_id
 where role.actor_type_code = 'prov_team'
   and role.cataloged_team_id is null
   and mention.post_id = role.post_id
   and team.team_name = role.actor_name
   and team.affiliated_organization_name
       is not distinct from role.affiliated_organization_name;

-- Organizations: copy a mention only when exactly one mentioned org on
-- that post has this role's actor_name. Two same-named mentions stay
-- unbound rather than guessing.
update post_summary_role role
   set cataloged_corporate_entity_id = matched.corporate_entity_id
  from (
        select mention.post_id,
               org.entity_name,
               min(org.corporate_entity_id::text)::uuid as corporate_entity_id
          from post_organization_mention mention
          join corporate_entity org
            on org.corporate_entity_id = mention.corporate_entity_id
         group by mention.post_id, org.entity_name
        having count(*) = 1
       ) matched
 where role.actor_type_code = 'prov_organization'
   and role.cataloged_corporate_entity_id is null
   and role.post_id = matched.post_id
   and role.actor_name = matched.entity_name;

-- ADR 0019 completion: persist the person catalog id resolved for an
-- R&R actor. Fetching by person_name is not identifying -- two people
-- can share a display name. Write-time persist orders by created_at,
-- then person_id. Historical backfill copies a mention only when
-- exactly one mentioned person on that post has this role's actor_name.

alter table post_summary_role
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
                + (cataloged_corporate_entity_id is not null)::int
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
                    cataloged_corporate_entity_id is null
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

-- People: copy a mention only when exactly one mentioned person on
-- that post has this role's actor_name. Two same-named mentions stay
-- unbound rather than guessing a UUID (Fellegi & Sunter, 1969).
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

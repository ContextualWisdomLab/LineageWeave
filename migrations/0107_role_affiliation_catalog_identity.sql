-- ADR 0127: an R&R person's/team's organization affiliation has its own
-- catalog identity. It must not reuse the actor identity columns because a
-- role can legitimately have both a person/team node and an organization node.

alter table post_summary_role
    add column if not exists cataloged_affiliated_corporate_entity_id uuid
        references corporate_entity (corporate_entity_id);

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_summary_role_affiliation_type_chk'
    ) then
        alter table post_summary_role
            add constraint post_summary_role_affiliation_type_chk check (
                cataloged_affiliated_corporate_entity_id is null
                or actor_type_code in ('prov_person', 'prov_team')
            );
    end if;
end
$$;

-- Cross-post identity resolution for R&R actors (ADR 0009). Extraction
-- runs per-post, but the same team, person, or organization named
-- across two different posts must resolve to the same catalog row --
-- otherwise every extraction is an island and can never become a
-- cross-post Knowledge Graph clue.
--
-- Teams (prov_team, ADR 0007) had no catalog at all until now, unlike
-- persons (cataloged_person, already Keyman's identity catalog) and
-- organizations (corporate_entity, already the corporate hierarchy
-- catalog). This migration adds the missing team catalog and two
-- mention join tables (post_team_mention, post_organization_mention)
-- so knowledge_graph_edge writers can derive Team/Organization mention
-- edges the same way they already derive Person mention edges from
-- post_person_mention.

create table if not exists cataloged_team (
    team_id uuid primary key default uuid_generate_v4(),
    team_name text not null,
    affiliated_organization_name text,
    affiliated_corporate_entity_id uuid references corporate_entity (corporate_entity_id),
    created_at timestamptz not null default now(),
    -- A team name alone rarely uniquely identifies it across a whole
    -- product's real-world scope ("설계팀" exists at many companies);
    -- the (name, org) pair almost always does. NULLS NOT DISTINCT makes
    -- a missing affiliation participate in the same identity key, so
    -- concurrent upserts of the same unplaced team return one row.
    unique nulls not distinct (team_name, affiliated_organization_name)
);

create index if not exists cataloged_team_corporate_entity_idx
    on cataloged_team (affiliated_corporate_entity_id)
    where affiliated_corporate_entity_id is not null;

create table if not exists post_team_mention (
    post_id uuid not null references source_post (post_id),
    team_id uuid not null references cataloged_team (team_id),
    primary key (post_id, team_id)
);

create table if not exists post_organization_mention (
    post_id uuid not null references source_post (post_id),
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    primary key (post_id, corporate_entity_id)
);

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('corporate_entity_level', 'group', 'Group', 0),
    ('corporate_entity_level', 'company', 'Company', 1),
    ('corporate_entity_level', 'plant', 'Plant', 2),
    ('node_type', 'node_team', 'Team', 3),
    ('edge_type', 'edge_mention_team', 'Team mentioned in', 3),
    ('edge_type', 'edge_team_affiliation', 'Team affiliated with', 4),
    ('edge_type', 'edge_mention_organization', 'Organization mentioned in', 5)
on conflict (lookup_code) do nothing;
-- Keyman and R&R person mentions are independent replaceable evidence
-- channels. The upgrade copies matching R&R actor names into
-- post_summary_person_mention and leaves post_person_mention (including
-- mention_context) untouched. combined_post_person_mention already unions
-- both sources; deleting Keyman rows would drop mention_context and let a
-- later persist_post_summary erase the only remaining person evidence.
create table if not exists post_summary_person_mention (
            post_id uuid not null references source_post (post_id) on delete cascade,
            person_id uuid not null references cataloged_person (person_id),
            primary key (post_id, person_id)
        );

        create or replace view combined_post_person_mention as
            select post_id, person_id from post_person_mention
            union
            select post_id, person_id from post_summary_person_mention;

        insert into post_summary_person_mention (post_id, person_id)
        select distinct role.post_id, matched_person.person_id
          from post_summary_role role
          join lateral (
                select person.person_id
                  from cataloged_person person
                 where person.person_name = role.actor_name
                 order by person.created_at, person.person_id
                 limit 1
          ) matched_person on true
         where role.actor_type_code = 'prov_person'
        on conflict do nothing;

        with ranked_edge as (
            select knowledge_graph_edge_id,
                   row_number() over (
                       partition by source_node_type_code, source_node_id,
                                    target_node_type_code, target_node_id,
                                    edge_type_code
                       order by created_at, knowledge_graph_edge_id
                   ) as duplicate_rank
              from knowledge_graph_edge
        )
        delete from knowledge_graph_edge edge_row
         using ranked_edge duplicate
         where edge_row.knowledge_graph_edge_id = duplicate.knowledge_graph_edge_id
           and duplicate.duplicate_rank > 1;

        create unique index if not exists knowledge_graph_edge_identity_uq
            on knowledge_graph_edge (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code
            );

        create table if not exists knowledge_graph_edge_evidence (
    knowledge_graph_edge_id uuid not null
        references knowledge_graph_edge (knowledge_graph_edge_id) on delete cascade,
    evidence_post_id uuid not null references source_post (post_id) on delete cascade,
    primary key (knowledge_graph_edge_id, evidence_post_id)
);

create index if not exists knowledge_graph_edge_evidence_post_idx
    on knowledge_graph_edge_evidence (evidence_post_id, knowledge_graph_edge_id);

create or replace function register_knowledge_graph_edge_evidence()
returns trigger
language plpgsql
as $$
begin
    if new.edge_type_code in (
        'edge_mention',
        'edge_mention_team',
        'edge_mention_organization'
    ) and new.target_node_type_code = 'node_post' then
        insert into knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        values (new.knowledge_graph_edge_id, new.target_node_id)
        on conflict do nothing;
    elsif new.edge_type_code = 'edge_co_mention' then
        insert into knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        select distinct new.knowledge_graph_edge_id, left_mention.post_id
          from combined_post_person_mention left_mention
          join combined_post_person_mention right_mention
            on right_mention.post_id = left_mention.post_id
         where left_mention.person_id = new.source_node_id
           and right_mention.person_id = new.target_node_id
        on conflict do nothing;
    elsif new.edge_type_code = 'edge_affiliation' then
        insert into knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        select distinct new.knowledge_graph_edge_id, mention.post_id
          from combined_post_person_mention mention
          join person_affiliation affiliation
            on affiliation.person_id = mention.person_id
         where mention.person_id = new.source_node_id
           and affiliation.affiliated_corporate_entity_id = new.target_node_id
        on conflict do nothing;
    elsif new.edge_type_code = 'edge_team_affiliation' then
        insert into knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        select distinct new.knowledge_graph_edge_id, mention.post_id
          from post_team_mention mention
          join cataloged_team team on team.team_id = mention.team_id
         where mention.team_id = new.source_node_id
           and team.affiliated_corporate_entity_id = new.target_node_id
        on conflict do nothing;
    end if;
    return new;
end
$$;

drop trigger if exists knowledge_graph_edge_evidence_register
    on knowledge_graph_edge;
create trigger knowledge_graph_edge_evidence_register
after insert or update on knowledge_graph_edge
for each row execute function register_knowledge_graph_edge_evidence();

        -- Re-run the support trigger for every surviving legacy edge, then prune
        -- rows that cannot be tied to current post evidence.
        update knowledge_graph_edge set edge_weight = edge_weight;
        delete from knowledge_graph_edge edge_row
         where not exists (
             select 1
               from knowledge_graph_edge_evidence evidence
              where evidence.knowledge_graph_edge_id = edge_row.knowledge_graph_edge_id
         );

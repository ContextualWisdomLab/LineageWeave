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
    -- the (name, org) pair almost always does. NULL org rows are not
    -- deduplicated by this constraint (standard SQL NULL semantics) --
    -- the application layer checks for an existing NULL-org row before
    -- inserting, so this is a backup, not the only guard.
    unique (team_name, affiliated_organization_name)
);

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
    ('node_type', 'node_team', 'Team', 3),
    ('edge_type', 'edge_mention_team', 'Team mentioned in', 3),
    ('edge_type', 'edge_team_affiliation', 'Team affiliated with', 4),
    ('edge_type', 'edge_mention_organization', 'Organization mentioned in', 5)
on conflict (lookup_code) do nothing;

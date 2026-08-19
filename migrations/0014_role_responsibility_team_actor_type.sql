-- A third roles-and-responsibilities actor case real data surfaced:
-- a named sub-unit of a company ("설계팀" [design team]) is meso-level --
-- neither a person nor the company itself. Adds `prov_team` alongside
-- `prov_person`/`prov_organization` (migration 0012); grounded in the
-- W3C Organization Ontology's org:OrganizationalUnit (see ADR 0007),
-- not PROV-O, which has no sub-organization concept. Purely additive:
-- no existing row's actor_type_code changes.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('prov_agent_type', 'prov_team', 'Team', 2)
on conflict (lookup_code) do nothing;

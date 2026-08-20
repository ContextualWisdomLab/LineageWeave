-- Keep verified organization resolutions linked by catalog identity, not name.
alter table organization_name_resolution
    add column if not exists resolved_corporate_entity_id uuid
        references corporate_entity (corporate_entity_id);

create index if not exists organization_name_resolution_entity_id_idx
    on organization_name_resolution (resolved_corporate_entity_id);

comment on column organization_name_resolution.resolved_corporate_entity_id is
    'Stable catalog identity for a corroborated resolution; null means the historical cache row has not been linked yet.';

-- ADR 0141: an explicit, nullable catalog_unresolved_reason_code so R&R can
-- distinguish why a person/organization actor has no catalog binding,
-- instead of one flat "Not linked to catalog" label for every cause. This
-- migration only adds the lookup values and the column -- it does not
-- backfill a reason onto historical rows (no reason is invented for history
-- the resolver never recorded); the frontend keeps its existing generic
-- label whenever the reason is null.
insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('catalog_unresolved_reason', 'reason_tied_candidates', 'Multiple equally likely matches', 0),
    ('catalog_unresolved_reason', 'reason_no_live_client', 'No live enrichment service configured', 1),
    ('catalog_unresolved_reason', 'reason_not_corroborated', 'Checked, not independently corroborated', 2),
    ('catalog_unresolved_reason', 'reason_no_catalog_entry', 'No matching catalog entry yet', 3)
on conflict (lookup_code) do nothing;

alter table post_summary_role
    add column if not exists catalog_unresolved_reason_code text
        references common_lookup_value (lookup_code);

-- The same closed vocabulary also covers why a role's *affiliated*
-- organization link (cataloged_affiliated_corporate_entity_id, ADR 0127)
-- is unbound -- this is the field the shipped "Not linked to catalog" label
-- actually renders next to (RoleEvidence.tsx), so it needs its own column
-- rather than sharing catalog_unresolved_reason_code with the primary actor.
alter table post_summary_role
    add column if not exists affiliation_catalog_unresolved_reason_code text
        references common_lookup_value (lookup_code);

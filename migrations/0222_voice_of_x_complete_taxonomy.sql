-- ADR 0232: complete general Voice-of-X taxonomy.
-- Extends the governed voc_type scheme from five to twelve codes and
-- mirrors the six new voice classes in entity_relationship_type so any
-- post can type its named counterparties. Additive only: existing rows,
-- codes, and display orders are untouched. Idempotent on replay, scoped
-- by category like migration 0042.

begin;

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('voc_type', 'vos', 'Voice of Supplier', 5),
    ('voc_type', 'voe', 'Voice of Employee', 6),
    ('voc_type', 'vob', 'Voice of Business', 7),
    ('voc_type', 'vor', 'Voice of Regulator', 8),
    ('voc_type', 'voi', 'Voice of Investor', 9),
    ('voc_type', 'voso', 'Voice of Society', 10),
    ('voc_type', 'vops', 'Voice of Process', 11)
on conflict (lookup_code) do update
    set lookup_category = excluded.lookup_category,
        lookup_label = excluded.lookup_label,
        display_order = excluded.display_order
    where common_lookup_value.lookup_category = 'voc_type';

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('entity_relationship_type', 'rel_voe', 'Employee-voice signal involving this organization', 6),
    ('entity_relationship_type', 'rel_vob', 'Internal-business-unit signal involving this organization', 7),
    ('entity_relationship_type', 'rel_vor', 'Regulates the post author''s organization', 8),
    ('entity_relationship_type', 'rel_voi', 'Invests in the post author''s organization', 9),
    ('entity_relationship_type', 'rel_voso', 'Community/society-level signal involving this organization', 10),
    ('entity_relationship_type', 'rel_vops', 'Process/system signal involving this organization', 11)
on conflict (lookup_code) do update
    set lookup_category = excluded.lookup_category,
        lookup_label = excluded.lookup_label,
        display_order = excluded.display_order
    where common_lookup_value.lookup_category = 'entity_relationship_type';

commit;

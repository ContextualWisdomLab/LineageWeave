-- Preserve the governed five-value VOC source vocabulary.
-- Existing source imports use VOC, VOCC, VOCO, VOM, and VOP; the importer
-- canonicalizes case while this lookup supplies the FK and UI labels.

begin;

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('voc_type', 'voc', 'Voice of Customer', 0),
    ('voc_type', 'vocc', 'Voice of Customer''s Customer', 1),
    ('voc_type', 'voco', 'Voice of Competitor', 2),
    ('voc_type', 'vom', 'Voice of Market', 3),
    ('voc_type', 'vop', 'Voice of Partner', 4)
on conflict (lookup_code) do update
    set lookup_category = excluded.lookup_category,
        lookup_label = excluded.lookup_label,
        display_order = excluded.display_order
    where common_lookup_value.lookup_category = 'voc_type';

commit;

-- ADR 0246: expanded Voice-of-X post taxonomy.
-- Adds seven source post voice codes without changing the independently
-- governed counterparty-relationship vocabulary. Additive only: existing
-- rows, codes, and display orders are untouched. Idempotent on replay,
-- scoped by category like migration 0042.

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

commit;

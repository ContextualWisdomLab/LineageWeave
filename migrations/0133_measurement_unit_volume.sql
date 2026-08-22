begin;

-- Volume/capacity units (m^3, L) were never seeded, so unit_code could
-- never persist for the only measurement_type ("capacity") that a volume
-- fact naturally belongs to -- extraction had to silently drop any such
-- measurement (see lineageweave.post_summary.MEASUREMENT_UNITS).
insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('measurement_unit', 'unit_m3', 'Cubic meter (m³)', 3),
    ('measurement_unit', 'unit_liter', 'Liter (L)', 4)
on conflict (lookup_code) do nothing;

commit;

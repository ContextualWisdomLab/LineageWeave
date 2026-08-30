-- Reverse 0245. Leftover distance, residual, unexplained leftover,
-- reconstruction, cross share, unexplained leftover share, and explained
-- leftover share stay on the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_person_axis_1,
    drop column if exists leftover_map_person_axis_2,
    drop column if exists leftover_map_item_axis_1,
    drop column if exists leftover_map_item_axis_2;

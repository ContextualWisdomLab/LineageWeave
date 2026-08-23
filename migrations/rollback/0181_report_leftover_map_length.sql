-- Reverse 0181. Leftover distance and residual stay on the pair row.

alter table report_leftover_pair
    drop constraint if exists report_leftover_pair_map_length_nonnegative;

alter table report_leftover_pair
    drop column if exists leftover_map_person_length,
    drop column if exists leftover_map_item_length;

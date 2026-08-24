-- Reverse 0186. Leftover distance, residual, Y, E, and rank stay on the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_reconstruction;

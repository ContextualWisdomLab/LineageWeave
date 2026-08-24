-- Reverse 0183. Leftover distance, residual, and unexplained leftover stay.

alter table report_leftover_pair
    drop column if exists leftover_map_reconstruction;

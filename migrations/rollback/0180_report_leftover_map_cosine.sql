-- Reverse 0180. Leftover distance and residual stay on the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_cosine;

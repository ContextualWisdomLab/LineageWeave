-- Reverse 0233. Leftover distance, residual, unexplained leftover,
-- reconstruction, and cross share stay on the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_unexplained_share;

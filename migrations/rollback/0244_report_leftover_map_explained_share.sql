-- Reverse 0244. Leftover distance, residual, unexplained leftover,
-- reconstruction, cross share, and unexplained leftover share stay on
-- the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_explained_share;

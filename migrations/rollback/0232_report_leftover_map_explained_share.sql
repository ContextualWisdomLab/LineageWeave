-- Reverse 0232. Leftover distance, residual, unexplained leftover,
-- cross share, and reconstruction stay on the pair row.

alter table report_leftover_pair
    drop column if exists leftover_map_explained_share;

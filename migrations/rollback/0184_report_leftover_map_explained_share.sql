-- Reverse 0184. Leftover distance and residual stay on the pair row.

alter table report_leftover_pair
    drop constraint if exists leftover_pair_explained_share_nonnegative_chk;

alter table report_leftover_pair
    drop column if exists leftover_map_explained_share;

-- Reverse 0202. Leftover distance and residual stay on the pair row.

alter table report_leftover_pair
    drop constraint if exists leftover_pair_unexplained_share_nonnegative_chk;

alter table report_leftover_pair
    drop column if exists leftover_map_unexplained_share;

-- ADR 0233: persist leftover-map unexplained leftover share
-- s = U² / R² of raw residual after two-axis leftover-map
-- reconstruction (R̂ = ξ_{1:2} · ζ_{1:2}, U = R − R̂). Distance stays
-- Euclidean leftover-map d. This migration adds only the unexplained-share
-- column. Upgrade column is nullable so older leftover rows keep distance,
-- residual, unexplained leftover, reconstruction, and cross share without
-- fabricating a share. This migration is the single source of the column
-- on fresh and existing installations. Do not edit shipped migrations
-- 0001 / 0012 after the fact. Do not persist leftover_map_explained_share.
-- Do not add an upper-bound CHECK: s may exceed 1 when |U| > |R|.

alter table report_leftover_pair
    add column if not exists leftover_map_unexplained_share numeric;

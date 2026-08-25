-- ADR 0185: persist leftover-map cross share x = 2 R̂ U / R² of raw
-- residual after two-axis leftover-map reconstruction
-- (R̂ = ξ_{1:2} · ζ_{1:2}, U = R − R̂). Distance stays Euclidean
-- leftover-map d. This migration adds only the cross-share column.
-- Upgrade column is nullable so older leftover rows keep distance and
-- residual without fabricating a share. This migration is the single
-- source of the column on fresh and existing installations. Do not
-- edit shipped migrations 0001 / 0012 after the fact. Do not persist
-- leftover_map_explained_share or leftover_map_unexplained_share.
-- Do not add a nonnegative CHECK: x may be negative when reconstruction
-- and unexplained leftover have opposite signs.

alter table report_leftover_pair
    add column if not exists leftover_map_cross_share numeric;

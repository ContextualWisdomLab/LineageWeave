-- ADR 0185: persist leftover-map cross share x = 2 R̂_c U_c / R̃² of
-- the centered leftover after two-axis leftover-map reconstruction
-- (R̃ = R − center, R̂_c = ξ_{1:2} · ζ_{1:2}, U_c = R̃ − R̂_c).
-- Distance stays Euclidean leftover-map d. Centered leftover U_c and
-- reconstruction R̂_c are computed internally and are not persisted.
-- Upgrade column is nullable so older leftover rows keep distance and
-- residual without fabricating a share. This migration is the single
-- source of the column on fresh and existing installations. Do not
-- edit shipped migrations 0001 / 0012 after the fact. Do not persist
-- leftover_map_explained_share, leftover_map_unexplained_share,
-- leftover_map_unexplained, or leftover_map_reconstruction.
-- Do not add a nonnegative CHECK: x may be negative when reconstruction
-- and unexplained leftover have opposite signs.

alter table report_leftover_pair
    add column if not exists leftover_map_cross_share numeric;

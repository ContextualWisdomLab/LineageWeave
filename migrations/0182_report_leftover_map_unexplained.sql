-- ADR 0182: persist unexplained leftover U = R − R̂ after two-axis
-- leftover-map reconstruction R̂ = ξ_{1:2} · ζ_{1:2}. Distance stays
-- Euclidean leftover-map d. Reconstruction is computed internally and
-- is not persisted. Upgrade column is nullable so older leftover rows
-- keep distance and residual without fabricating unexplained leftover.
-- This migration is the single source of the column on fresh and
-- existing installations.

alter table report_leftover_pair
    add column if not exists leftover_map_unexplained numeric;

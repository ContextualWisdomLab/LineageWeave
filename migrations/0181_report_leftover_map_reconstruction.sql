-- ADR 0181: persist two-axis leftover-map reconstruction R̂ = ξ_{1:2} · ζ_{1:2}
-- on leftover post–criterion pairs. Distance stays Euclidean leftover-map d.
-- Upgrade column is nullable so older leftover rows keep distance and
-- residual without fabricating a reconstruction. This migration is the
-- single source of the column on fresh and existing installations.

alter table report_leftover_pair
    add column if not exists leftover_map_reconstruction numeric;

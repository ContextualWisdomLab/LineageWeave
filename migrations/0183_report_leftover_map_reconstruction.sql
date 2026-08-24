-- ADR 0183: persist leftover-map reconstruction R̂ = ξ_{1:2} · ζ_{1:2}
-- so unexplained leftover U = R − R̂ stays auditable as U + R̂ = R.
-- Distance stays Euclidean leftover-map d. No nonnegative CHECK: a
-- signed reconstruction is stored, never clamped. Upgrade column is
-- nullable so older leftover rows keep distance, residual, and
-- unexplained leftover without fabricating reconstruction. This
-- migration is the single source of the column on fresh and existing
-- installations.

alter table report_leftover_pair
    add column if not exists leftover_map_reconstruction numeric;

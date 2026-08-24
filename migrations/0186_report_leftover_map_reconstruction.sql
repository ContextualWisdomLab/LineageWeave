-- ADR 0186: persist leftover-map reconstruction on leftover post–criterion pairs.
-- Reconstruction is two-axis Gabriel inner product R̂_c = ξ_{1:2} · ζ_{1:2}
-- of centered leftover. Upgrade columns are nullable so older leftover
-- rows keep distance and residual without fabricating a reconstruction.
-- No nonnegative CHECK: reconstruction may be negative. This sequential
-- migration is the single source of the column on every install path.

alter table report_leftover_pair
    add column if not exists leftover_map_reconstruction double precision;

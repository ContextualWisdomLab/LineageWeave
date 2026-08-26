-- ADR 0232: persist leftover-map explained share e = Rhat^2 / R^2 of raw
-- residual after the Rust-owned two-axis leftover-map reconstruction.
-- Distance stays Euclidean leftover-map d. Upgrade column is nullable so
-- older rows retain their evidence without fabricating a share. Do not add a
-- unit or nonnegative CHECK: truncated reconstruction can make |Rhat| > |R|.

alter table report_leftover_pair
    add column if not exists leftover_map_explained_share numeric;

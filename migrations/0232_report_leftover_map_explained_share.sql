-- ADR 0232: persist leftover-map explained share e = R̂² / R² of raw
-- residual after two-axis leftover-map reconstruction
-- (R̂ = ξ_{1:2} · ζ_{1:2}). Distance stays Euclidean leftover-map d.
-- This migration adds only the explained-share column. Upgrade column
-- is nullable so older leftover rows keep distance, residual,
-- unexplained leftover, cross share, and reconstruction without
-- fabricating a share. This migration is the single source of the
-- column on fresh and existing installations. Do not edit shipped
-- migrations 0001 / 0012 after the fact. Do not persist
-- leftover_map_unexplained_share. Do not add a unit or nonnegative
-- CHECK: truncated two-axis reconstruction can make |R̂| > |R|.

alter table report_leftover_pair
    add column if not exists leftover_map_explained_share numeric;

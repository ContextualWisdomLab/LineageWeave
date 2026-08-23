-- ADR 0180: persist leftover-map cosine on leftover post–criterion
-- pairs. Distance stays Euclidean leftover-map d. Upgrade column is
-- nullable so older leftover rows keep distance and residual without
-- fabricating alignment. This migration is the single source of the
-- column on fresh and existing installations.

alter table report_leftover_pair
    add column if not exists leftover_map_cosine numeric;

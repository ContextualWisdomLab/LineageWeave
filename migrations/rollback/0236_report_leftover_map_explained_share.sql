-- Reverse migration 0236. Other leftover-map evidence remains available.

alter table report_leftover_pair
    drop column if exists leftover_map_explained_share;

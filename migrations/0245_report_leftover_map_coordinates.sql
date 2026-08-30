-- ADR 0267: persist leftover-map coordinates ξ_{1:2} and ζ_{1:2}
-- after two-axis leftover-map reconstruction (R̂ = ξ_{1:2} · ζ_{1:2})
-- and two-axis leftover-map distance (d = ‖ξ_{1:2} − ζ_{1:2}‖).
-- Distance stays Euclidean leftover-map d. This migration adds only the
-- four coordinate columns. Upgrade columns are nullable so older leftover
-- rows keep distance, residual, unexplained leftover, reconstruction,
-- cross share, unexplained leftover share, and explained leftover share
-- without fabricating a location. This migration is the single source of
-- the columns on fresh and existing installations. Do not edit shipped
-- migrations 0001 / 0012 after the fact. Do not add an upper-bound or
-- nonnegative CHECK: signed coordinates are stored, never clamped.

alter table report_leftover_pair
    add column if not exists leftover_map_person_axis_1 numeric,
    add column if not exists leftover_map_person_axis_2 numeric,
    add column if not exists leftover_map_item_axis_1 numeric,
    add column if not exists leftover_map_item_axis_2 numeric;

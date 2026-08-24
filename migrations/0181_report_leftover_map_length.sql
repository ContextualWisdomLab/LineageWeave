-- ADR 0181: persist leftover-map lengths ‖ξ‖ and ‖ζ‖ on leftover
-- post–criterion pairs. Distance stays Euclidean leftover-map d.
-- Upgrade columns are nullable so older leftover rows keep distance
-- and residual without fabricating lengths. This migration is the
-- single source of the columns on fresh and existing installations.

alter table report_leftover_pair
    add column if not exists leftover_map_person_length numeric,
    add column if not exists leftover_map_item_length numeric;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'report_leftover_pair_map_length_nonnegative'
    ) then
        alter table report_leftover_pair
            add constraint report_leftover_pair_map_length_nonnegative
            check (
                (leftover_map_person_length is null or leftover_map_person_length >= 0)
                and (leftover_map_item_length is null or leftover_map_item_length >= 0)
            );
    end if;
end $$;

-- ADR 0164: persist leftover-map rank on leftover post–criterion pairs.
-- Rank is the number of Gabriel singular values above the leftover
-- singular floor. Upgrade columns are nullable so older leftover rows
-- keep distance and residual without fabricating a rank. Fresh 0001 /
-- 0012 tables require the column.

alter table report_leftover_pair
    add column if not exists leftover_map_rank integer;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_map_rank_nonnegative_chk'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_map_rank_nonnegative_chk
            check (
                leftover_map_rank is null
                or leftover_map_rank >= 0
            );
    end if;
end $$;

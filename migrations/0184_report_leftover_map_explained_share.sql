-- ADR 0184: persist explained leftover share e = R̂_c² / R̃² of the
-- centered leftover the two-axis leftover map reconstructs
-- (R̃ = R − center, R̂_c = ξ_{1:2} · ζ_{1:2}).
-- Distance stays Euclidean leftover-map d. Centered leftover U_c and
-- reconstruction R̂_c are computed internally and are not persisted.
-- Upgrade column is nullable so older leftover rows keep distance and
-- residual without fabricating a share. This migration is the single
-- source of the column on fresh and existing installations. Do not
-- edit shipped migrations 0001 / 0012 after the fact. Do not persist
-- leftover_map_unexplained_share, leftover_map_unexplained, or
-- leftover_map_reconstruction.

alter table report_leftover_pair
    add column if not exists leftover_map_explained_share numeric;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_explained_share_nonnegative_chk'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_explained_share_nonnegative_chk
            check (
                leftover_map_explained_share is null
                or leftover_map_explained_share >= 0
            );
    end if;
end
$$;

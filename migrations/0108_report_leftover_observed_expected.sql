-- ADR 0168: persist observed Y and expected E[Y|θ, item] on leftover pairs
-- so leftover_residual is checkable as Y − E. Existing leftover rows are
-- derived; delete incomplete rows so rebuild/seed rewrites honest scores.
-- Never invent a leftover score or a second theta.

alter table report_leftover_pair
    add column if not exists leftover_observed_score numeric,
    add column if not exists leftover_expected_score numeric;

delete from report_leftover_pair
where leftover_observed_score is null
   or leftover_expected_score is null;

alter table report_leftover_pair
    alter column leftover_observed_score set not null,
    alter column leftover_expected_score set not null;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_residual_identity'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_residual_identity
            check (
                abs(leftover_residual - (leftover_observed_score - leftover_expected_score))
                < 1e-9
            );
    end if;
end $$;

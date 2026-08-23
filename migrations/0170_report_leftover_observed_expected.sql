-- ADR 0170: persist observed Y and expected E[Y|θ, item] on leftover
-- post–criterion pairs. Residual stays R = Y − E. Upgrade columns are
-- nullable so older leftover rows keep distance and residual without
-- fabricating Y or E. This migration is the single source of both columns
-- on fresh and existing installations.

alter table report_leftover_pair
    add column if not exists observed_response numeric;
alter table report_leftover_pair
    add column if not exists expected_response numeric;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'leftover_pair_observed_expected_reconcile_chk'
    ) then
        alter table report_leftover_pair
            add constraint leftover_pair_observed_expected_reconcile_chk
            check (
                (observed_response is null and expected_response is null)
                or (
                    observed_response is not null
                    and expected_response is not null
                    and abs(leftover_residual - (observed_response - expected_response)) < 1e-6
                )
            );
    end if;
end $$;

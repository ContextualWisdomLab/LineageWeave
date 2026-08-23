-- Reverse migration 0108. Leftover pairs remain; observed/expected
-- columns and the residual-identity check are removed.

begin;

alter table report_leftover_pair
    drop constraint if exists leftover_pair_residual_identity;

alter table report_leftover_pair
    drop column if exists leftover_observed_score,
    drop column if exists leftover_expected_score;

commit;

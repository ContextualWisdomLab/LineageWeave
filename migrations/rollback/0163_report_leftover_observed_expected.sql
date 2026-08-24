-- Reverse 0163. Leftover distance and residual stay on the pair row.

alter table report_leftover_pair
    drop constraint if exists leftover_pair_observed_expected_reconcile_chk;
alter table report_leftover_pair
    drop column if exists observed_response;
alter table report_leftover_pair
    drop column if exists expected_response;

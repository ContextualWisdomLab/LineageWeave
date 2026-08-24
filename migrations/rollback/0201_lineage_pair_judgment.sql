-- Rollback of 0201: the queued-judging ledger is derived operator state.
drop table if exists lineage_pair_judgment;
drop table if exists lineage_weight_estimation_run;

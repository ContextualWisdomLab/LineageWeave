-- The ownership-table rollback owns destructive removal of this guard.
-- Keeping the guard live until that rollback's preconditions succeed prevents a
-- failed recovery from exposing durable retired seed history to TRUNCATE CASCADE.
begin;

-- Intentionally no DDL here. rollback/0247_z_customer_master_translation_seed_ownership.sql
-- removes the trigger and function in the same transaction that successfully
-- removes the ownership table. If that rollback fails closed, this guard stays.

commit;

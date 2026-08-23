-- Rollback for 0135: drop the persisted channel-weight table. Rebuilds
-- fall back to the documented in-code constants (ADR 0145 fallback).

drop table if exists lineage_channel_weight;

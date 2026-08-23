-- The session, turn, and citation tables are shared with the existing Global
-- Ask context contract; only the 0126 projections are owned by this migration.
drop table if exists global_ask_turn_evidence;
drop table if exists global_ask_turn_source;

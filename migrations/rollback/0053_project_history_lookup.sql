begin;

drop index if exists post_lineage_edge_child_history_idx;
drop index if exists post_project_mention_name_history_idx;
drop index if exists post_project_mention_key_history_idx;
drop index if exists source_post_project_name_history_idx;
drop index if exists source_post_project_code_history_idx;
drop index if exists source_post_project_history_recent_idx;

commit;

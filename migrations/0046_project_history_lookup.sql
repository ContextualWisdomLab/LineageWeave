begin;

-- Exact NFKC/lower lookup keys keep explicit and semantic project evidence
-- indexable without changing the underlying source or inference truth status.
create index if not exists source_post_project_code_history_idx
    on source_post (
        lower(normalize(btrim(source_project_code), NFKC)),
        created_at,
        post_id
    )
    where source_project_code is not null and btrim(source_project_code) <> '';

create index if not exists source_post_project_name_history_idx
    on source_post (
        lower(normalize(btrim(source_project_name), NFKC)),
        created_at,
        post_id
    )
    where source_project_name is not null and btrim(source_project_name) <> '';

create index if not exists post_project_mention_name_history_idx
    on post_project_mention (
        lower(normalize(btrim(project_name), NFKC)),
        post_id
    );

create index if not exists post_lineage_edge_child_history_idx
    on post_lineage_edge (child_post_id, parent_post_id)
    include (fused_score);

commit;

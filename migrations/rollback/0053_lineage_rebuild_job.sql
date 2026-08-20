drop table if exists lineage_rebuild_job_status_event;
drop table if exists lineage_rebuild_job;

delete from common_lookup_value
where lookup_code in (
    'lineage_rebuild_queued',
    'lineage_rebuild_running',
    'lineage_rebuild_succeeded',
    'lineage_rebuild_failed',
    'lineage_rebuild_cancelled',
    'lineage_llm_requested',
    'lineage_llm_available',
    'lineage_llm_completed',
    'lineage_llm_skipped',
    'lineage_llm_failed',
    'lineage_llm_unavailable'
);

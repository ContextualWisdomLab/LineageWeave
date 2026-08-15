-- Roll back only migration 0018's normalized analysis-run control plane.
-- Existing source_post, lineage, Knowledge Graph, report, and provenance_* data
-- remain untouched. This script is intentionally explicit so an operator can
-- review every destructive object before execution.

begin;

drop table if exists analysis_artifact_record;
drop table if exists analysis_service_run;
drop table if exists analysis_run_event;
drop table if exists analysis_run_configuration;
drop table if exists analysis_run_record;
drop table if exists analysis_source_snapshot;
drop table if exists analysis_source_profile;

delete from common_lookup_value
where lookup_code in (
    'postgresql_query_profile',
    'analysis_run_running',
    'analysis_run_succeeded',
    'analysis_run_failed',
    'analysis_run_started_event',
    'analysis_run_completed_event',
    'analysis_run_failed_event',
    'analysis_service_tepp',
    'analysis_service_orchestrator',
    'analysis_service_fast_mlsirm',
    'analysis_service_running',
    'analysis_service_succeeded',
    'analysis_service_failed',
    'analysis_aggregate_manifest',
    'analysis_reproducibility_manifest',
    'analysis_browser_evidence'
);

commit;

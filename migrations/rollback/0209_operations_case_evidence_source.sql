alter table operations_case_fact
    drop constraint if exists operations_case_fact_evidence_post_fk,
    drop constraint if exists operations_case_fact_evidence_digest_check,
    drop column if exists evidence_post_id,
    drop column if exists evidence_input_sha256;
alter table operations_case_classification
    drop constraint if exists operations_case_classification_evidence_post_fk,
    drop constraint if exists operations_case_classification_evidence_digest_check,
    drop column if exists evidence_post_id,
    drop column if exists evidence_input_sha256;

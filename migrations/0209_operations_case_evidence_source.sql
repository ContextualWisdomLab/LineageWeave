-- ADR 0206: every inferred classification and fact names its analyzed source document.
alter table operations_case_classification
    add column if not exists evidence_post_id uuid,
    add column if not exists evidence_input_sha256 text;

update operations_case_classification
   set evidence_post_id = post_id
 where evidence_post_id is null;
update operations_case_classification classification
   set evidence_input_sha256 = analysis.source_body_sha256
  from operations_case_analysis analysis
 where analysis.post_id = classification.post_id
   and classification.evidence_input_sha256 is null;

alter table operations_case_classification
    alter column evidence_post_id set not null,
    alter column evidence_input_sha256 set not null;

alter table operations_case_classification
    drop constraint if exists operations_case_classification_evidence_post_fk,
    add constraint operations_case_classification_evidence_post_fk
        foreign key (evidence_post_id) references source_post(post_id) on delete restrict,
    drop constraint if exists operations_case_classification_evidence_digest_check,
    add constraint operations_case_classification_evidence_digest_check
        check (evidence_input_sha256 ~ '^[0-9a-f]{64}$');

alter table operations_case_fact
    add column if not exists evidence_post_id uuid,
    add column if not exists evidence_input_sha256 text;

update operations_case_fact fact
   set evidence_post_id = classification.evidence_post_id,
       evidence_input_sha256 = classification.evidence_input_sha256
  from operations_case_classification classification
 where classification.post_id = fact.post_id
   and classification.case_kind_code = fact.case_kind_code
   and (fact.evidence_post_id is null or fact.evidence_input_sha256 is null);

alter table operations_case_fact
    alter column evidence_post_id set not null,
    alter column evidence_input_sha256 set not null;

alter table operations_case_fact
    drop constraint if exists operations_case_fact_evidence_post_fk,
    add constraint operations_case_fact_evidence_post_fk
        foreign key (evidence_post_id) references source_post(post_id) on delete restrict,
    drop constraint if exists operations_case_fact_evidence_digest_check,
    add constraint operations_case_fact_evidence_digest_check
        check (evidence_input_sha256 ~ '^[0-9a-f]{64}$');

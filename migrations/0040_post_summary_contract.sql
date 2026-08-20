begin;

alter table post_summary_result
    add column if not exists summary_contract_version integer;

-- Rows written before the evidence-grounded summary contract are stale. They
-- remain available for audit but must not bypass contextual-orchestrator.
update post_summary_result
   set summary_contract_version = 0
 where summary_contract_version is null;

comment on column post_summary_result.summary_contract_version is
    'Summary extraction contract version; stale rows are regenerated from source_post.post_body.';

commit;

begin;

-- External search and internal corpus evidence are separate signals. Keep the
-- existing verification status for the web result and retain the authorized
-- source post that supplied internal context alongside it.
alter table post_counterparty_entity
    add column if not exists verification_evidence_post_id uuid
        references source_post(post_id);

create index if not exists post_counterparty_internal_evidence_idx
    on post_counterparty_entity (verification_evidence_post_id);

comment on column post_counterparty_entity.verification_evidence_post_id is
    'A visible source_post whose normalized text contains the named organization and relationship context.';

commit;

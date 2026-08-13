-- Relation-verification evidence status for post_counterparty_entity.
--
-- entity_relationship_classification.py's LLM classification names an
-- organization and a VOC/VOM/VOP/VOCC/VOCO/VOS relationship it has to the
-- post author's org -- an inference, not a directly observed fact. This
-- migration adds the evidence-status columns lineageweave/
-- relation_verification.py's external search agent (Searxng) writes to,
-- so a classified relationship carries a machine-checkable corroboration
-- status instead of being trusted at face value forever. Grounded in
-- FEVER-style open-domain claim verification (Thorne, Vlachos,
-- Christodoulopoulos, & Mittal, 2018): a claim is checked against
-- retrieved external evidence, not just the model that produced it.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('relation_verification_status', 'verify_pending', 'Not yet checked', 0),
    ('relation_verification_status', 'verify_corroborated', 'Corroborated by external search', 1),
    ('relation_verification_status', 'verify_uncorroborated', 'No corroborating evidence found', 2)
on conflict (lookup_code) do nothing;

alter table post_counterparty_entity
    add column if not exists verification_status_code text not null default 'verify_pending'
        references common_lookup_value (lookup_code);

alter table post_counterparty_entity
    add column if not exists verification_evidence_url text;

alter table post_counterparty_entity
    add column if not exists verification_checked_at timestamptz;

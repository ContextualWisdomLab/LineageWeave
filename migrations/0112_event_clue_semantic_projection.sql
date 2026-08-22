-- ADR 0129: source-grounded event observations and connected clues.
-- The compact KG remains the navigation projection; these rows retain the
-- evidence-bearing semantic path used by Ask and the KG renderer.

alter table post_summary_event
    add column if not exists evidence_text text,
    add column if not exists ontology_iri text not null default
        'https://contextualwisdomlab.github.io/lineageweave/ontology#KeyEvent',
    add column if not exists extraction_method text not null default
        'legacy_summary_event';

create table if not exists post_summary_event_clue (
    post_id uuid not null,
    event_ordinal integer not null,
    clue_ordinal integer not null,
    clue_type_code text not null,
    clue_text text not null,
    target_text text,
    normalized_value_text text,
    assertion_code text,
    evidence_text text not null,
    ontology_iri text not null,
    extraction_method text not null,
    primary key (post_id, event_ordinal, clue_ordinal),
    foreign key (post_id, event_ordinal)
        references post_summary_event (post_id, event_ordinal)
        on delete cascade,
    check (assertion_code is null or assertion_code in
        ('assertion_affirmed', 'assertion_negated', 'assertion_unknown'))
);

create index if not exists post_summary_event_clue_post_idx
    on post_summary_event_clue (post_id, clue_type_code, event_ordinal);

create index if not exists post_summary_event_clue_search_idx
    on post_summary_event_clue (post_id, clue_text, target_text, evidence_text);

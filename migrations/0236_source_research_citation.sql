-- ADR 0274: persist post-scoped source-unit / image-region research citations.
-- Replay-safe. Lookup codes are globally unique on lookup_code.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('source_research_lead_kind', 'research_lead_semantic_unit', 'Source semantic unit', 0),
    ('source_research_lead_kind', 'research_lead_image_region', 'Source image region', 1),
    ('source_research_judgment', 'research_supported', 'Supported by cited public resource', 0),
    ('source_research_judgment', 'research_refuted', 'Conflicts with cited public resource', 1),
    ('source_research_judgment', 'research_not_enough_information', 'Not enough public information', 2),
    ('source_research_judgment', 'research_unavailable', 'Public research unavailable', 3)
on conflict (lookup_code) do nothing;

create table if not exists source_research_citation (
    source_research_citation_id uuid primary key default gen_random_uuid(),
    post_id uuid not null references source_post(post_id) on delete cascade,
    lead_kind_code text not null references common_lookup_value(lookup_code),
    lead_source_unit_id uuid references post_content_unit(post_content_unit_id) on delete cascade,
    lead_image_region_id uuid
        references post_content_image_region(post_content_image_region_id) on delete cascade,
    lead_excerpt_text text not null,
    search_query_text text not null,
    evidence_url text,
    evidence_title_text text,
    evidence_excerpt_text text,
    judgment_code text not null references common_lookup_value(lookup_code),
    rationale_text text not null default '',
    next_action_text text not null,
    checked_at timestamptz not null default now(),
    constraint source_research_citation_lead_kind_check check (
        (
            lead_kind_code = 'research_lead_semantic_unit'
            and lead_source_unit_id is not null
            and lead_image_region_id is null
        )
        or (
            lead_kind_code = 'research_lead_image_region'
            and lead_image_region_id is not null
            and lead_source_unit_id is null
        )
    )
);

create index if not exists source_research_citation_post_idx
    on source_research_citation (post_id, checked_at desc);

create unique index if not exists source_research_citation_unit_uidx
    on source_research_citation (post_id, lead_source_unit_id)
    where lead_source_unit_id is not null;

create unique index if not exists source_research_citation_region_uidx
    on source_research_citation (post_id, lead_image_region_id)
    where lead_image_region_id is not null;

comment on table source_research_citation is
    'Latest public-research judgment for one source unit or image region lead.';

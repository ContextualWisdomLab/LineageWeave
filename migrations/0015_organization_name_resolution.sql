-- Caches an abbreviated/slang organization name's LLM-inferred
-- canonical name plus external search cross-verification (ADR 0008),
-- e.g. "한수원" -> "한국수력원자력". corporate_hierarchy_resolution's
-- character-similarity matching cannot bridge this gap (an initialism
-- shares almost no substring with its expansion), so a genuine
-- LLM-context + web-evidence step is needed instead. Keyed by the raw
-- name so the same abbreviation across many posts is resolved once.

create table if not exists organization_name_resolution (
    raw_organization_name text primary key,
    resolved_organization_name text not null,
    verification_status_code text not null references common_lookup_value (lookup_code),
    verification_evidence_url text,
    resolved_at timestamptz not null default now()
);

comment on table organization_name_resolution is
    'Caches LLM-proposed canonical names for abbreviated/slang organization mentions (e.g. 한수원 -> 한국수력원자력), cross-verified via external search before being trusted.';

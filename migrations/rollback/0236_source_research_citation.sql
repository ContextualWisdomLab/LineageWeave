-- ADR 0268 rollback for migration 0236.
drop index if exists source_research_citation_region_uidx;
drop index if exists source_research_citation_unit_uidx;
drop index if exists source_research_citation_post_idx;
drop table if exists source_research_citation;

delete from common_lookup_value
 where lookup_code in (
    'research_lead_semantic_unit',
    'research_lead_image_region',
    'research_supported',
    'research_refuted',
    'research_not_enough_information',
    'research_unavailable'
 );

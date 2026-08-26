begin;

drop trigger if exists public_claim_envelope_require_public_post
    on public_claim_envelope;
drop function if exists public_claim_envelope_require_public_post();
drop table if exists public_claim_envelope;

delete from common_lookup_value
 where lookup_code in (
    'claim_organization_presence',
    'claim_public_event',
    'claim_public_relationship',
    'claim_unavailable',
    'claim_supported',
    'claim_refuted',
    'claim_not_enough_information'
);

commit;

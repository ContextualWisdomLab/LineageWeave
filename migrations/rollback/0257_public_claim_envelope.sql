drop trigger if exists revoke_private_public_claim_envelopes on source_post;
drop function if exists revoke_private_public_claim_envelopes();
drop trigger if exists validate_public_claim_envelope on public_claim_envelope;
drop function if exists validate_public_claim_envelope();
drop table if exists public_claim_envelope;

begin;

drop trigger if exists public_claim_envelope_require_public_post
    on public_claim_envelope;
drop function if exists public_claim_envelope_require_public_post();
drop table if exists public_claim_envelope;

do $$
begin
    if exists (
        select 1 from information_schema.columns
         where table_schema = 'public'
           and table_name = 'global_ask_job'
           and column_name = 'verify_external'
    ) then
        alter table global_ask_job drop column verify_external;
    end if;
end $$;

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

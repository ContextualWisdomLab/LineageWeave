begin;

alter table post_content_unit
    add column if not exists source_evidence_reference text;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_content_unit_source_evidence_reference_check'
           and conrelid = 'post_content_unit'::regclass
    ) then
        alter table post_content_unit
            add constraint post_content_unit_source_evidence_reference_check
            check (
                source_evidence_reference is null
                or (
                    source_evidence_reference = btrim(source_evidence_reference)
                    and char_length(source_evidence_reference) >= 1
                    and octet_length(source_evidence_reference) <= 24000
                )
            ) not valid;
    end if;
end
$$;

commit;

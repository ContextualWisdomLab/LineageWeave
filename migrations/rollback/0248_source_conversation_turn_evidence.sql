alter table post_content_unit
    drop constraint if exists post_content_unit_source_evidence_reference_check;

alter table post_content_unit
    drop column if exists source_evidence_reference;

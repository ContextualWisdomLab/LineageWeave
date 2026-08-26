-- ADR 0250: preserve the official release document and construct descriptions.

alter table occupational_construct_vocabulary
    add column if not exists source_content_sha256 text;

alter table occupational_construct_vocabulary
    drop constraint if exists occupational_construct_vocabulary_source_content_sha256_check;
alter table occupational_construct_vocabulary
    add constraint occupational_construct_vocabulary_source_content_sha256_check
    check (
        source_content_sha256 is null
        or source_content_sha256 ~ '^[0-9a-f]{64}$'
    );

alter table occupational_construct
    add column if not exists construct_description text;

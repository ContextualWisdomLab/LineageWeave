-- ADR 0052 / 0098 / 0114: bind a summary to its normalized input evidence.

alter table post_summary_result
    add column if not exists summary_input_sha256 text;

alter table post_summary_result
    drop constraint if exists post_summary_result_summary_input_sha256_check;

alter table post_summary_result
    add constraint post_summary_result_summary_input_sha256_check check (
        summary_input_sha256 is null
        or summary_input_sha256 ~ '^[0-9a-f]{64}$'
    );

comment on column post_summary_result.summary_input_sha256 is
    'SHA-256 of the exact normalized text or ordered persisted image evidence summarized';

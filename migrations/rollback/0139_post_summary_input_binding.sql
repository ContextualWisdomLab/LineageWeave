-- Roll back the normalized summary-input binding introduced by migration 0139.

alter table post_summary_result
    drop constraint if exists post_summary_result_summary_input_sha256_check;

alter table post_summary_result
    drop column if exists summary_input_sha256;

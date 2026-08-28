-- ADR 0206: bind operational case reuse to the exact authorized input window.
alter table operations_case_analysis
    add column if not exists analysis_input_sha256 text;

alter table operations_case_analysis
    drop constraint if exists operations_case_analysis_input_digest_check,
    add constraint operations_case_analysis_input_digest_check
        check (
            analysis_input_sha256 is null
            or analysis_input_sha256 ~ '^[0-9a-f]{64}$'
        );

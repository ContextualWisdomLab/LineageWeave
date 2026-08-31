-- Migration 0272 / ADR 0228: receipt-bound product analysis completion.
alter table post_product_analysis
    add column if not exists orchestrator_model_receipt text;

alter table post_product_analysis
    drop constraint if exists post_product_analysis_model_receipt_check,
    add constraint post_product_analysis_model_receipt_check
        check (
            orchestrator_model_receipt is null
            or btrim(orchestrator_model_receipt) <> ''
        );

create index if not exists post_product_analysis_receipt_digest_idx
    on post_product_analysis (source_body_sha256, post_id)
    where orchestrator_model_receipt is not null;

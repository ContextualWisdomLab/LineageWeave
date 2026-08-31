drop index if exists post_product_analysis_receipt_digest_idx;

alter table post_product_analysis
    drop constraint if exists post_product_analysis_model_receipt_check,
    drop column if exists orchestrator_model_receipt;

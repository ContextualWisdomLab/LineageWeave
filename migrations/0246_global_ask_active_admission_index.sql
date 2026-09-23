create index concurrently if not exists global_ask_job_active_account_idx
    on global_ask_job (requesting_account_id)
    where job_status_code in ('queued', 'running');

CREATE TABLE IF NOT EXISTS common_enum_values (
    enum_family text NOT NULL,
    enum_code text NOT NULL,
    enum_label text NOT NULL,
    sort_order integer NOT NULL DEFAULT 0,
    PRIMARY KEY (enum_family, enum_code)
);

INSERT INTO common_enum_values (enum_family, enum_code, enum_label, sort_order) VALUES
    ('entity_role', '파트너', 'Partner', 1),
    ('entity_role', '경쟁사', 'Competitor', 2),
    ('entity_role', '고객', 'Customer', 3),
    ('entity_role', '고객의 고객', 'End customer', 4),
    ('entity_role', '시장', 'Market', 5),
    ('visibility', 'public', 'Public', 1),
    ('visibility', 'private', 'Private', 2),
    ('ticket_status', 'open', '접수됨', 1),
    ('ticket_status', 'in_progress', '진행 중', 2),
    ('ticket_status', 'resolved', '해결됨', 3),
    ('judge_verdict', 'pass', 'Pass', 1),
    ('judge_verdict', 'fail', 'Fail', 2),
    ('judge_verdict', 'abstain', 'Abstain', 3),
    ('judge_verdict', 'unavailable', 'Unavailable', 4),
    ('tepp_run_state', 'accepted', 'Accepted', 1),
    ('tepp_run_state', 'validating', 'Validating', 2),
    ('tepp_run_state', 'queued', 'Queued', 3),
    ('tepp_run_state', 'running', 'Running', 4),
    ('tepp_run_state', 'verifying', 'Verifying', 5),
    ('tepp_run_state', 'completed', 'Completed', 6),
    ('tepp_run_state', 'failed', 'Failed', 7),
    ('tepp_run_state', 'rejected', 'Rejected', 8),
    ('tepp_run_state', 'retryable', 'Retryable', 9),
    ('tepp_run_state', 'cancelling', 'Cancelling', 10),
    ('tepp_run_state', 'cancelled', 'Cancelled', 11),
    ('enrichment_task', 'keyman', 'Keyman', 1),
    ('enrichment_task', 'product', 'R&R and issue work', 2),
    ('enrichment_task', 'appointments', 'Customer appointments', 3),
    ('enrichment_task', 'all', 'All pending enrichment', 4)
ON CONFLICT (enum_family, enum_code) DO NOTHING;

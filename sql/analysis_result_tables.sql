CREATE TABLE IF NOT EXISTS analysis_run_records (
    run_stamp timestamptz NOT NULL DEFAULT now(),
    row_count integer NOT NULL,
    document_count integer NOT NULL,
    thread_count integer NOT NULL,
    metadata_payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_tepp_run_records (
    tepp_run_id text PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    actor_account_id text NOT NULL,
    corp_code text NOT NULL,
    pu_code text NOT NULL,
    snapshot_id text NOT NULL,
    knowledge_cutoff text NOT NULL,
    model_contract jsonb NOT NULL,
    configuration jsonb NOT NULL,
    output_profile jsonb NOT NULL,
    request_sha256 text NOT NULL,
    remote_state text NOT NULL,
    request_id text NOT NULL DEFAULT '',
    retryable boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_document_nodes (
    document_no text PRIMARY KEY,
    acthguid text,
    title_sample text,
    corp_code text,
    owner_pu text,
    entity_role text,
    visibility_code text,
    korean_summary text,
    keyman_source text,
    keyman_status text,
    keyman_our_side jsonb NOT NULL DEFAULT '[]'::jsonb,
    keyman_counterpart_side jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS analysis_lineage_edges (
    source_node text NOT NULL,
    target_node text NOT NULL,
    relation_name text NOT NULL,
    evidence_status text NOT NULL,
    acthguid text
);

CREATE TABLE IF NOT EXISTS analysis_lineage_edge_overrides (
    source_node text NOT NULL,
    target_node text NOT NULL,
    relation_name text NOT NULL,
    override_status text NOT NULL,
    reason text NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_node, target_node, relation_name)
);

CREATE TABLE IF NOT EXISTS analysis_event_outbox (
    event_id text PRIMARY KEY,
    event_type text NOT NULL,
    document_no text NOT NULL,
    actor_id text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);

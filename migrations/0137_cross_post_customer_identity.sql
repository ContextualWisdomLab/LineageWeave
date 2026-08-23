INSERT INTO common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
VALUES
    ('customer_identity_status', 'customer_identity_abstained', 'Abstained', 0),
    ('customer_identity_status', 'customer_identity_promoted', 'Promoted', 1),
    ('customer_identity_criterion', 'customer_cross_post_recurrence', 'Cross-post recurrence', 0),
    ('customer_identity_criterion', 'customer_same_organization', 'Same organization', 1),
    ('customer_identity_criterion', 'customer_candidate_name_support', 'Candidate name support', 2),
    ('customer_rename_criterion', 'customer_rename_same_identity', 'Rename preserves identity', 0),
    ('customer_rename_criterion', 'customer_rename_explicit_change', 'Explicit name change', 1),
    ('customer_rename_criterion', 'customer_rename_temporal_successor', 'Temporal name succession', 2),
    ('corporate_entity_name_role', 'entity_name_preferred', 'Preferred name', 0),
    ('corporate_entity_name_role', 'entity_name_former', 'Former name', 1),
    ('corporate_entity_name_role', 'entity_name_alternate', 'Alternate name', 2),
    ('edge_type', 'edge_customer_identity_observation', 'Customer identity observation', 6)
ON CONFLICT (lookup_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS customer_identity_judgment (
    customer_identity_judgment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system_code TEXT,
    source_customer_code TEXT NOT NULL CHECK (btrim(source_customer_code) <> ''),
    candidate_entity_name TEXT NOT NULL CHECK (btrim(candidate_entity_name) <> ''),
    evidence_sha256 TEXT NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    judgment_status_code TEXT NOT NULL REFERENCES common_lookup_value(lookup_code),
    rubric_version TEXT NOT NULL,
    distinct_post_count INTEGER NOT NULL CHECK (distinct_post_count >= 2),
    judge_score NUMERIC NOT NULL CHECK (judge_score >= 0 AND judge_score <= 1),
    judge_accepted BOOLEAN NOT NULL,
    judge_rationale TEXT NOT NULL CHECK (btrim(judge_rationale) <> ''),
    orchestration_mode TEXT NOT NULL CHECK (btrim(orchestration_mode) <> ''),
    trace_step_count INTEGER NOT NULL CHECK (trace_step_count >= 0),
    rename_judge_score NUMERIC CHECK (rename_judge_score >= 0 AND rename_judge_score <= 1),
    rename_judge_accepted BOOLEAN,
    rename_judge_rationale TEXT,
    temporal_order_source_code TEXT NOT NULL
        CHECK (temporal_order_source_code IN ('source_timestamp', 'tepp')),
    verification_evidence_url TEXT,
    corporate_entity_id UUID REFERENCES corporate_entity(corporate_entity_id),
    judged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (rename_judge_score IS NULL)::INTEGER
        + (rename_judge_accepted IS NULL)::INTEGER
        + (rename_judge_rationale IS NULL)::INTEGER IN (0, 3)
    ),
    CONSTRAINT customer_identity_judgment_evidence_unique
        UNIQUE NULLS NOT DISTINCT
        (source_system_code, source_customer_code, evidence_sha256, rubric_version)
);

CREATE TABLE IF NOT EXISTS customer_identity_judgment_response (
    customer_identity_judgment_id UUID NOT NULL
        REFERENCES customer_identity_judgment(customer_identity_judgment_id)
        ON DELETE CASCADE,
    criterion_code TEXT NOT NULL REFERENCES common_lookup_value(lookup_code),
    criterion_score NUMERIC NOT NULL CHECK (criterion_score >= 0 AND criterion_score <= 1),
    response_category INTEGER NOT NULL CHECK (response_category BETWEEN 0 AND 4),
    PRIMARY KEY (customer_identity_judgment_id, criterion_code)
);

COMMENT ON TABLE customer_identity_judgment IS
    'One versioned cross-post customer-identity decision for an exact source key and evidence fingerprint.';
COMMENT ON TABLE customer_identity_judgment_response IS
    'Criterion-level fast-mlsirm IRT responses supporting a customer-identity decision.';

CREATE TABLE IF NOT EXISTS customer_identity_judgment_post (
    customer_identity_judgment_id UUID NOT NULL
        REFERENCES customer_identity_judgment(customer_identity_judgment_id)
        ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES source_post(post_id) ON DELETE CASCADE,
    evidence_ordinal INTEGER NOT NULL CHECK (evidence_ordinal >= 0),
    observed_customer_name TEXT,
    excerpt_sha256 TEXT NOT NULL CHECK (excerpt_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (customer_identity_judgment_id, post_id),
    CONSTRAINT customer_identity_judgment_post_ordinal_unique
        UNIQUE (customer_identity_judgment_id, evidence_ordinal)
);

COMMENT ON TABLE customer_identity_judgment_post IS
    'Normalized post evidence membership for one cross-post customer-identity decision.';

CREATE INDEX IF NOT EXISTS customer_identity_judgment_post_lookup_idx
    ON customer_identity_judgment_post(post_id, customer_identity_judgment_id);

CREATE TABLE IF NOT EXISTS customer_identity_binding (
    customer_identity_binding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system_code TEXT,
    source_customer_code TEXT NOT NULL CHECK (btrim(source_customer_code) <> ''),
    corporate_entity_id UUID NOT NULL REFERENCES corporate_entity(corporate_entity_id),
    customer_identity_judgment_id UUID NOT NULL
        REFERENCES customer_identity_judgment(customer_identity_judgment_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT customer_identity_binding_source_unique
        UNIQUE NULLS NOT DISTINCT (source_system_code, source_customer_code)
);

COMMENT ON TABLE customer_identity_binding IS
    'Stable Customer Master binding for one source-system and customer-code key.';

CREATE INDEX IF NOT EXISTS customer_identity_binding_entity_idx
    ON customer_identity_binding(corporate_entity_id, source_system_code, source_customer_code);

CREATE TABLE IF NOT EXISTS corporate_entity_name_history (
    corporate_entity_name_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporate_entity_id UUID NOT NULL
        REFERENCES corporate_entity(corporate_entity_id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL CHECK (btrim(entity_name) <> ''),
    name_role_code TEXT NOT NULL REFERENCES common_lookup_value(lookup_code),
    observed_from TIMESTAMPTZ NOT NULL,
    observed_to TIMESTAMPTZ,
    customer_identity_judgment_id UUID
        REFERENCES customer_identity_judgment(customer_identity_judgment_id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (observed_to IS NULL OR observed_to >= observed_from)
);

COMMENT ON TABLE corporate_entity_name_history IS
    'Preferred, former, and alternate organization names with observation intervals.';

CREATE UNIQUE INDEX IF NOT EXISTS corporate_entity_current_name_unique
    ON corporate_entity_name_history(corporate_entity_id)
    WHERE name_role_code = 'entity_name_preferred' AND observed_to IS NULL;

CREATE INDEX IF NOT EXISTS corporate_entity_name_lookup_idx
    ON corporate_entity_name_history(lower(entity_name), corporate_entity_id);

INSERT INTO corporate_entity_name_history (
    corporate_entity_id, entity_name, name_role_code, observed_from
)
SELECT entity.corporate_entity_id, entity.entity_name,
       'entity_name_preferred', entity.created_at
  FROM corporate_entity entity
 WHERE NOT EXISTS (
     SELECT 1 FROM corporate_entity_name_history history
      WHERE history.corporate_entity_id = entity.corporate_entity_id
        AND history.name_role_code = 'entity_name_preferred'
        AND history.observed_to IS NULL
 );

CREATE TABLE IF NOT EXISTS post_customer_identity_mention (
    post_id UUID NOT NULL REFERENCES source_post(post_id) ON DELETE CASCADE,
    corporate_entity_id UUID NOT NULL
        REFERENCES corporate_entity(corporate_entity_id) ON DELETE CASCADE,
    customer_identity_judgment_id UUID NOT NULL
        REFERENCES customer_identity_judgment(customer_identity_judgment_id)
        ON DELETE CASCADE,
    PRIMARY KEY (post_id, corporate_entity_id)
);

COMMENT ON TABLE post_customer_identity_mention IS
    'Post-scoped evidence that a governed Customer Master identity was observed.';

CREATE INDEX IF NOT EXISTS post_customer_identity_entity_idx
    ON post_customer_identity_mention(corporate_entity_id, post_id);

CREATE OR REPLACE FUNCTION register_knowledge_graph_edge_evidence()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.edge_type_code IN (
        'edge_mention',
        'edge_mention_team',
        'edge_mention_organization',
        'edge_customer_identity_observation'
    ) AND NEW.target_node_type_code = 'node_post' THEN
        INSERT INTO knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        SELECT NEW.knowledge_graph_edge_id, NEW.target_node_id
         WHERE EXISTS (
             SELECT 1 FROM source_post post
              WHERE post.post_id = NEW.target_node_id
         )
        ON CONFLICT DO NOTHING;
    ELSIF NEW.edge_type_code = 'edge_co_mention' THEN
        INSERT INTO knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        SELECT DISTINCT NEW.knowledge_graph_edge_id, left_mention.post_id
          FROM combined_post_person_mention left_mention
          JOIN combined_post_person_mention right_mention
            ON right_mention.post_id = left_mention.post_id
         WHERE left_mention.person_id = NEW.source_node_id
           AND right_mention.person_id = NEW.target_node_id
        ON CONFLICT DO NOTHING;
    ELSIF NEW.edge_type_code = 'edge_affiliation' THEN
        INSERT INTO knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        SELECT DISTINCT NEW.knowledge_graph_edge_id, mention.post_id
          FROM combined_post_person_mention mention
          JOIN person_affiliation affiliation
            ON affiliation.person_id = mention.person_id
         WHERE mention.person_id = NEW.source_node_id
           AND affiliation.affiliated_corporate_entity_id = NEW.target_node_id
        ON CONFLICT DO NOTHING;
    ELSIF NEW.edge_type_code = 'edge_team_affiliation' THEN
        INSERT INTO knowledge_graph_edge_evidence
            (knowledge_graph_edge_id, evidence_post_id)
        SELECT DISTINCT NEW.knowledge_graph_edge_id, mention.post_id
          FROM post_team_mention mention
          JOIN cataloged_team team ON team.team_id = mention.team_id
         WHERE mention.team_id = NEW.source_node_id
           AND team.affiliated_corporate_entity_id = NEW.target_node_id
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END
$$;

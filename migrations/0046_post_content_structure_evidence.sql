CREATE TABLE IF NOT EXISTS post_content_unit_structure (
    post_content_unit_structure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_content_unit_id UUID NOT NULL REFERENCES post_content_unit(post_content_unit_id) ON DELETE CASCADE,
    indent_level INTEGER NOT NULL DEFAULT 0 CHECK (indent_level >= 0),
    decision_source_code TEXT NOT NULL CHECK (decision_source_code IN ('explicit', 'llm', 'unresolved')),
    confidence NUMERIC(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT post_content_unit_structure_unit_unique UNIQUE (post_content_unit_id)
);

CREATE INDEX IF NOT EXISTS idx_post_content_unit_structure_source
    ON post_content_unit_structure (decision_source_code);

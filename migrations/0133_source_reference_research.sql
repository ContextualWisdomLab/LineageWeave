INSERT INTO common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
VALUES
    ('source_reference_type', 'source_reference_url', 'URL reference', 0),
    ('source_reference_type', 'source_reference_patent', 'Patent reference', 1),
    ('source_research_status', 'research_supported', 'Supported', 0),
    ('source_research_status', 'research_refuted', 'Refuted', 1),
    ('source_research_status', 'research_not_enough_information', 'Not enough information', 2)
ON CONFLICT (lookup_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS post_source_research_lead (
    post_source_research_lead_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES source_post(post_id) ON DELETE CASCADE,
    source_content_unit_id UUID REFERENCES post_content_unit(post_content_unit_id) ON DELETE CASCADE,
    source_image_region_id UUID REFERENCES post_content_image_region(post_content_image_region_id) ON DELETE CASCADE,
    lead_ordinal INTEGER NOT NULL CHECK (lead_ordinal >= 0),
    lead_type_code TEXT NOT NULL REFERENCES common_lookup_value(lookup_code),
    query_text TEXT NOT NULL CHECK (btrim(query_text) <> ''),
    evidence_text TEXT NOT NULL CHECK (btrim(evidence_text) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT post_source_research_lead_ordinal_unique UNIQUE (post_id, lead_ordinal),
    CONSTRAINT post_source_research_lead_source_check CHECK (
        (source_content_unit_id IS NOT NULL)::INTEGER
        + (source_image_region_id IS NOT NULL)::INTEGER = 1
    )
);

CREATE TABLE IF NOT EXISTS post_source_research_retrieval (
    post_source_research_retrieval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_source_research_lead_id UUID NOT NULL REFERENCES post_source_research_lead(post_source_research_lead_id) ON DELETE CASCADE,
    retrieval_ordinal INTEGER NOT NULL CHECK (retrieval_ordinal >= 0),
    evidence_url TEXT NOT NULL CHECK (evidence_url ~ '^https?://'),
    evidence_title TEXT NOT NULL,
    passage_text TEXT NOT NULL CHECK (btrim(passage_text) <> ''),
    content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT post_source_research_retrieval_ordinal_unique UNIQUE (post_source_research_lead_id, retrieval_ordinal),
    CONSTRAINT post_source_research_retrieval_lead_identity_unique UNIQUE (post_source_research_lead_id, post_source_research_retrieval_id)
);

CREATE TABLE IF NOT EXISTS post_source_research_judgment (
    post_source_research_judgment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_source_research_lead_id UUID NOT NULL UNIQUE REFERENCES post_source_research_lead(post_source_research_lead_id) ON DELETE CASCADE,
    research_status_code TEXT NOT NULL REFERENCES common_lookup_value(lookup_code),
    sharing_actor_name TEXT,
    rationale_text TEXT NOT NULL CHECK (btrim(rationale_text) <> ''),
    judged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT post_source_research_judgment_lead_identity_unique UNIQUE (post_source_research_lead_id, post_source_research_judgment_id)
);

CREATE TABLE IF NOT EXISTS post_source_research_citation (
    post_source_research_citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_source_research_lead_id UUID NOT NULL REFERENCES post_source_research_lead(post_source_research_lead_id) ON DELETE CASCADE,
    post_source_research_judgment_id UUID NOT NULL,
    post_source_research_retrieval_id UUID NOT NULL,
    CONSTRAINT post_source_research_citation_judgment_fk FOREIGN KEY
        (post_source_research_lead_id, post_source_research_judgment_id)
        REFERENCES post_source_research_judgment
        (post_source_research_lead_id, post_source_research_judgment_id)
        ON DELETE CASCADE,
    CONSTRAINT post_source_research_citation_retrieval_fk FOREIGN KEY
        (post_source_research_lead_id, post_source_research_retrieval_id)
        REFERENCES post_source_research_retrieval
        (post_source_research_lead_id, post_source_research_retrieval_id)
        ON DELETE CASCADE,
    CONSTRAINT post_source_research_citation_unique UNIQUE (post_source_research_judgment_id, post_source_research_retrieval_id)
);

CREATE INDEX IF NOT EXISTS post_source_research_lead_post_idx
    ON post_source_research_lead (post_id, lead_ordinal);

-- Repair an earlier partial application of this migration without discarding
-- private runtime evidence.
ALTER TABLE post_source_research_lead
    ADD COLUMN IF NOT EXISTS source_content_unit_id UUID REFERENCES post_content_unit(post_content_unit_id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS source_image_region_id UUID REFERENCES post_content_image_region(post_content_image_region_id) ON DELETE CASCADE;

ALTER TABLE post_source_research_citation
    ADD COLUMN IF NOT EXISTS post_source_research_lead_id UUID;
UPDATE post_source_research_citation citation
   SET post_source_research_lead_id = judgment.post_source_research_lead_id
  FROM post_source_research_judgment judgment
 WHERE citation.post_source_research_judgment_id = judgment.post_source_research_judgment_id
   AND citation.post_source_research_lead_id IS NULL;
ALTER TABLE post_source_research_citation
    ALTER COLUMN post_source_research_lead_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_lead'::regclass
           AND conname = 'post_source_research_lead_source_check'
    ) THEN
        ALTER TABLE post_source_research_lead
            ADD CONSTRAINT post_source_research_lead_source_check CHECK (
                (source_content_unit_id IS NOT NULL)::INTEGER
                + (source_image_region_id IS NOT NULL)::INTEGER = 1
            );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_retrieval'::regclass
           AND conname = 'post_source_research_retrieval_lead_identity_unique'
    ) THEN
        ALTER TABLE post_source_research_retrieval
            ADD CONSTRAINT post_source_research_retrieval_lead_identity_unique
            UNIQUE (post_source_research_lead_id, post_source_research_retrieval_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_judgment'::regclass
           AND conname = 'post_source_research_judgment_lead_identity_unique'
    ) THEN
        ALTER TABLE post_source_research_judgment
            ADD CONSTRAINT post_source_research_judgment_lead_identity_unique
            UNIQUE (post_source_research_lead_id, post_source_research_judgment_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_citation'::regclass
           AND conname = 'post_source_research_citation_lead_fk'
    ) THEN
        ALTER TABLE post_source_research_citation
            ADD CONSTRAINT post_source_research_citation_lead_fk
            FOREIGN KEY (post_source_research_lead_id)
            REFERENCES post_source_research_lead(post_source_research_lead_id)
            ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_citation'::regclass
           AND conname = 'post_source_research_citation_judgment_fk'
    ) THEN
        ALTER TABLE post_source_research_citation
            ADD CONSTRAINT post_source_research_citation_judgment_fk
            FOREIGN KEY (post_source_research_lead_id, post_source_research_judgment_id)
            REFERENCES post_source_research_judgment
                (post_source_research_lead_id, post_source_research_judgment_id)
            ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'post_source_research_citation'::regclass
           AND conname = 'post_source_research_citation_retrieval_fk'
    ) THEN
        ALTER TABLE post_source_research_citation
            ADD CONSTRAINT post_source_research_citation_retrieval_fk
            FOREIGN KEY (post_source_research_lead_id, post_source_research_retrieval_id)
            REFERENCES post_source_research_retrieval
                (post_source_research_lead_id, post_source_research_retrieval_id)
            ON DELETE CASCADE;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION validate_post_source_research_owner()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.source_content_unit_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM post_content_unit
         WHERE post_content_unit_id = NEW.source_content_unit_id
           AND post_id = NEW.post_id
    ) THEN
        RAISE EXCEPTION 'source research content unit belongs to another post';
    END IF;
    IF NEW.source_image_region_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
          FROM post_content_image_region region
          JOIN post_content_image image USING (post_content_image_id)
          JOIN post_content_unit unit USING (post_content_unit_id)
         WHERE region.post_content_image_region_id = NEW.source_image_region_id
           AND unit.post_id = NEW.post_id
    ) THEN
        RAISE EXCEPTION 'source research image region belongs to another post';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS validate_post_source_research_owner_trigger
    ON post_source_research_lead;
CREATE TRIGGER validate_post_source_research_owner_trigger
BEFORE INSERT OR UPDATE OF post_id, source_content_unit_id, source_image_region_id
ON post_source_research_lead
FOR EACH ROW EXECUTE FUNCTION validate_post_source_research_owner();

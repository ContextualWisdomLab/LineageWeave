-- ADR 0256: index assertion-backed catalog labels for authorized search.
-- pg_trgm is created by 0032; IF NOT EXISTS keeps replay safe (ADR 0166).

create index if not exists occupational_construct_preferred_label_trgm_idx
    on occupational_construct using gin (preferred_label gin_trgm_ops);

create index if not exists occupational_construct_description_trgm_idx
    on occupational_construct using gin (construct_description gin_trgm_ops);

create index if not exists post_occupational_construct_assertion_construct_post_idx
    on post_occupational_construct_assertion (construct_id, post_id, generated_at);

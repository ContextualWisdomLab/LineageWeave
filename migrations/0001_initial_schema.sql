-- LineageWeave product schema, migration 0001.
--
-- Third normal form: every non-key column depends on the whole primary
-- key and nothing but the primary key. Enum-like values are never stored
-- as redundant label text next to a code -- they live once in
-- common_lookup_value and everything else references the code.
--
-- Naming: snake_case, two or more words, per this project's convention
-- (see AGENTS.md / CLAUDE.md).
--
-- Identity and content are synthetic-only in this repository's default
-- configuration -- see docs/adr/0001-demo-identity-and-data-boundary.md.

begin;

create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------
-- Shared configuration: every ENUM-like value lives here once, grouped
-- by lookup_category, so a new classification value never needs a new
-- table or a new column -- just a new row.
-- ---------------------------------------------------------------------
create table common_lookup_value (
    lookup_category text not null,
    lookup_code text not null,
    lookup_label text not null,
    display_order integer not null default 0,
    primary key (lookup_category, lookup_code),
    -- A referencing column (e.g. post.voc_type_code) only ever names the
    -- code, not the category -- the category is implied by which column
    -- it is. That means a single-column FK must target a unique
    -- lookup_code, so codes are unique across ALL categories, not just
    -- within one (e.g. 'draft' can't be both a ticket_status code and a
    -- post_visibility code). Deliberate simplification: invent distinct
    -- code names per category rather than adding a second FK column to
    -- every referencing table for what is, in practice, a small fixed
    -- vocabulary. Revisit with a composite FK per referencing column if
    -- a future category's codes genuinely need to collide with another's.
    unique (lookup_code)
);

comment on table common_lookup_value is
    'Every ENUM-like value in this schema (voc_type, post_visibility, '
    'entity_relationship_type, person_side, edge_type, node_type, '
    'ticket_status, permission, corporate_entity_level, '
    'relation_verification_status, evaluation_criterion) lives here once. '
    'lookup_code is unique across all categories -- see the unique(lookup_code) comment.';

-- ---------------------------------------------------------------------
-- Corporate structure: a self-referencing tree so a query can walk
-- "Acme Group -> Acme Electronics Korea -> Acme Electronics HQ ->
-- Acme Electronics Gwangju Plant" without a fixed number of levels.
-- ---------------------------------------------------------------------
create table corporate_entity (
    corporate_entity_id uuid primary key default uuid_generate_v4(),
    parent_entity_id uuid references corporate_entity (corporate_entity_id),
    -- The short code carried as the "corp code" attribute at login time
    -- (see docker/keycloak/realm-export.json's corp_code claim) -- distinct
    -- from entity_name, which is the human-readable hierarchy label.
    corporate_entity_code text not null unique,
    entity_name text not null,
    entity_level_code text not null references common_lookup_value (lookup_code),
    created_at timestamptz not null default now()
);

create index corporate_entity_parent_idx on corporate_entity (parent_entity_id);

create table process_unit (
    process_unit_id uuid primary key default uuid_generate_v4(),
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    process_unit_code text not null unique,
    process_unit_name text not null
);

create index process_unit_entity_idx on process_unit (corporate_entity_id);

-- ---------------------------------------------------------------------
-- Accounts. Login uses a real OIDC subject (external_subject_id) --
-- corp code / PU code are ATTRIBUTES of an account (via
-- account_affiliation), never the login key itself, per the product
-- requirement that corp/PU code selection happens after authentication.
-- ---------------------------------------------------------------------
create table user_account (
    user_account_id uuid primary key default uuid_generate_v4(),
    external_subject_id text not null unique,
    display_name text not null,
    email_address text not null,
    created_at timestamptz not null default now()
);

create table account_affiliation (
    account_affiliation_id uuid primary key default uuid_generate_v4(),
    user_account_id uuid not null references user_account (user_account_id),
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    process_unit_id uuid references process_unit (process_unit_id),
    unique (user_account_id, corporate_entity_id, process_unit_id)
);

create index account_affiliation_user_idx on account_affiliation (user_account_id);

-- ---------------------------------------------------------------------
-- RBAC: coarse role membership.
-- ---------------------------------------------------------------------
create table access_role (
    access_role_id uuid primary key default uuid_generate_v4(),
    role_code text not null unique,
    role_name text not null
);

create table role_permission (
    access_role_id uuid not null references access_role (access_role_id),
    permission_code text not null references common_lookup_value (lookup_code),
    primary key (access_role_id, permission_code)
);

create table account_role_assignment (
    user_account_id uuid not null references user_account (user_account_id),
    access_role_id uuid not null references access_role (access_role_id),
    primary key (user_account_id, access_role_id)
);

-- ---------------------------------------------------------------------
-- ABAC: fine-grained policy evaluated against request attributes
-- (requesting account's corp/PU code, resource visibility, etc.) on top
-- of RBAC's coarser role gate. condition_expression is a small,
-- store-your-own-DSL text field (e.g. JSONLogic) -- deliberately not
-- modeled as further tables here; document the DSL choice when Phase 1's
-- backend implements the evaluator.
-- ---------------------------------------------------------------------
create table abac_policy (
    abac_policy_id uuid primary key default uuid_generate_v4(),
    policy_name text not null,
    policy_effect text not null check (policy_effect in ('allow', 'deny')),
    resource_type_code text not null references common_lookup_value (lookup_code),
    action_code text not null references common_lookup_value (lookup_code),
    condition_expression text not null,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Source posts (the scattered records this whole project reconstructs
-- lineage between). Named source_post, not post, so every table name
-- is two or more snake_case words.
-- ---------------------------------------------------------------------
create table source_post (
    post_id uuid primary key default uuid_generate_v4(),
    author_account_id uuid not null references user_account (user_account_id),
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    process_unit_id uuid references process_unit (process_unit_id),
    post_title text not null,
    post_body text not null,
    voc_type_code text not null references common_lookup_value (lookup_code),
    visibility_code text not null references common_lookup_value (lookup_code),
    -- Reconstruct grouping keys persisted as-is. Do not derive these from
    -- process_unit_id or voc_type_code: those collapse A-100/B-200 and
    -- proj-alpha/proj-beta and lose the designed fork on rebuild.
    thread_group_key text not null default '',
    secondary_grouping_key text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index post_corporate_entity_idx on source_post (corporate_entity_id);
create index post_author_idx on source_post (author_account_id);

-- Counterparty entities named IN a post's content, classified by
-- relationship type (partner / competitor / customer / customer's
-- customer / market / ...). Free-text name because a counterparty is
-- rarely already a row in corporate_entity.
-- verification_* columns: relation_verification.py's external search
-- agent (Searxng) checks this LLM-inferred relationship against the web
-- and records the outcome, so a hallucinated organization/relationship
-- doesn't sit indistinguishable from a corroborated one. See
-- migrations/0004_relation_verification.sql / ADR 0005.
create table post_counterparty_entity (
    post_id uuid not null references source_post (post_id),
    counterparty_entity_name text not null,
    relationship_type_code text not null references common_lookup_value (lookup_code),
    verification_status_code text not null default 'verify_pending'
        references common_lookup_value (lookup_code),
    verification_evidence_url text,
    verification_checked_at timestamptz,
    primary key (post_id, counterparty_entity_name)
);

-- One IRT response-matrix cell per post per rubric criterion. Written
-- only from fast_mlsirm.LLMJudgeResult.to_irt_row() (ADR 0003 slice 2).
create table post_evaluation_response (
    post_id uuid not null references source_post (post_id),
    criterion_code text not null references common_lookup_value (lookup_code),
    rubric_version text not null,
    response_category integer not null,
    judged_at timestamptz not null default now(),
    primary key (post_id, criterion_code, rubric_version)
);

create index post_evaluation_response_post_idx on post_evaluation_response (post_id);

-- Persisted popup summary. Seed writes a synthetic row so GET
-- /api/posts/{id}/summary is not empty without a live LLM.
create table post_summary_result (
    post_id uuid primary key references source_post (post_id) on delete cascade,
    korean_summary text not null,
    computed_at timestamptz not null default now()
);

create table post_summary_event (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    event_ordinal integer not null,
    event_text text not null,
    primary key (post_id, event_ordinal)
);

create table post_summary_role (
    post_id uuid not null references post_summary_result (post_id) on delete cascade,
    person_name text not null,
    responsibility text not null,
    primary key (post_id, person_name)
);

-- Persisted in-popup Q&A. Seed writes a synthetic exchange so
-- GET/POST /api/posts/{id}/chat is not empty without a live LLM.
-- Live answers still write through the same tables. Never invent a
-- reply: a missing (post, question) pair 503s when the orchestrator
-- is off.
create table post_chat_result (
    post_id uuid not null references source_post (post_id) on delete cascade,
    question_norm text not null,
    question_text text not null,
    answer_text text not null,
    computed_at timestamptz not null default now(),
    primary key (post_id, question_norm)
);

create table post_chat_citation (
    post_id uuid not null,
    question_norm text not null,
    citation_ordinal integer not null,
    cited_post_id uuid not null references source_post (post_id) on delete cascade,
    primary key (post_id, question_norm, citation_ordinal),
    foreign key (post_id, question_norm)
        references post_chat_result (post_id, question_norm) on delete cascade
);

-- Calibrated period scores (ADR 0003 slice 3/4). Written only by
-- lineageweave.period_report.link_or_calibrate_period_report.
-- link_method = free on the first period; fipc on later periods scored
-- against report_item_parameter from the anchor period.
create table report_period_score (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    selected_model text not null,
    mean_theta numeric not null,
    mean_theta_sd numeric not null,
    post_count integer not null,
    item_count integer not null,
    fit_loglik numeric not null,
    fit_converged boolean not null,
    calibration_score numeric not null,
    link_method text not null default 'free',
    anchor_period_code text,
    delta_mean_theta numeric,
    computed_at timestamptz not null default now(),
    primary key (grouping_kind, grouping_key, period_code, rubric_version),
    check (grouping_kind in ('process_unit', 'corporate_entity', 'thread_group', 'shared_metric')),
    check (link_method in ('free', 'fipc'))
);

create table report_member_score (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    post_id uuid not null references source_post (post_id),
    theta_eap numeric not null,
    theta_sd numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, post_id),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

create index report_member_score_post_idx on report_member_score (post_id);

-- Fixed item parameters for the period's metric. Later weeks copy the
-- earliest free-calibrated bank so EAP thetas stay comparable.
create table report_item_parameter (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    item_code text not null,
    item_index integer not null,
    slope numeric not null,
    cat_params numeric[] not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, item_code),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade
);

-- CAT item-information ranking on the shared bank (ADR 0003 slice 6).
-- Rank 1 is the Lord (1980) max-info pick at the group's mean θ.
create table report_item_information (
    grouping_kind text not null,
    grouping_key text not null,
    period_code text not null,
    rubric_version text not null,
    item_code text not null,
    item_rank integer not null,
    information numeric not null,
    primary key (grouping_kind, grouping_key, period_code, rubric_version, item_code),
    foreign key (grouping_kind, grouping_key, period_code, rubric_version)
        references report_period_score (grouping_kind, grouping_key, period_code, rubric_version)
        on delete cascade,
    check (item_rank >= 1)
);

-- ---------------------------------------------------------------------
-- Keyman: real (or, in this repo's default synthetic configuration,
-- fabricated -- see ADR 0001) people mentioned in posts. A person may
-- have N affiliations (an internal Keyman can span multiple group
-- companies; a counterparty Keyman can span multiple external orgs).
-- ---------------------------------------------------------------------
-- Cataloged people mentioned in posts (Keyman). Named cataloged_person,
-- not person, so every table name is two or more snake_case words.
create table cataloged_person (
    person_id uuid primary key default uuid_generate_v4(),
    person_name text not null,
    person_side_code text not null references common_lookup_value (lookup_code),
    created_at timestamptz not null default now()
);

create table person_affiliation (
    person_affiliation_id uuid primary key default uuid_generate_v4(),
    person_id uuid not null references cataloged_person (person_id),
    affiliated_organization_name text not null,
    affiliated_corporate_entity_id uuid references corporate_entity (corporate_entity_id),
    role_title text,
    unique (person_id, affiliated_organization_name)
);

create index person_affiliation_person_idx on person_affiliation (person_id);

create table post_person_mention (
    post_id uuid not null references source_post (post_id),
    person_id uuid not null references cataloged_person (person_id),
    mention_context text,
    primary key (post_id, person_id)
);

-- ---------------------------------------------------------------------
-- Knowledge graph: person/company/post nodes, typed edges. The type
-- codes (which kind of node, which kind of edge) are real enums and DO
-- reference common_lookup_value. The *_node_id columns are the
-- genuinely polymorphic part and intentionally have no FK constraint --
-- a single edge table spanning heterogeneous node types cannot both
-- stay in one table and enforce a per-type FK on the id column in
-- standard SQL. Documented deliberate denormalization; the application
-- layer validates node existence per type at write time.
-- ---------------------------------------------------------------------
create table knowledge_graph_edge (
    knowledge_graph_edge_id uuid primary key default uuid_generate_v4(),
    source_node_type_code text not null references common_lookup_value (lookup_code),
    source_node_id uuid not null,
    target_node_type_code text not null references common_lookup_value (lookup_code),
    target_node_id uuid not null,
    edge_type_code text not null references common_lookup_value (lookup_code),
    edge_weight numeric not null default 1.0,
    created_at timestamptz not null default now()
);

create index knowledge_graph_edge_source_idx on knowledge_graph_edge (source_node_type_code, source_node_id);
create index knowledge_graph_edge_target_idx on knowledge_graph_edge (target_node_type_code, target_node_id);

-- ---------------------------------------------------------------------
-- Issue tickets tied to a post.
-- ---------------------------------------------------------------------
create table issue_ticket (
    issue_ticket_id uuid primary key default uuid_generate_v4(),
    post_id uuid not null references source_post (post_id),
    ticket_status_code text not null references common_lookup_value (lookup_code),
    ticket_title text not null,
    assigned_account_id uuid references user_account (user_account_id),
    -- When set, this ticket is also a calendar/to-do entry (GET /api/calendar) --
    -- e.g. a customer commitment an LLM derived from the post's own text via
    -- POST /api/posts/{post_id}/derive-commitment. NULL for an ordinary
    -- ticket with no date attached.
    due_date date,
    -- LLM-authored description of the commitment this ticket represents
    -- (distinct from ticket_title, which may be a shorter user-facing label).
    commitment_summary text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index issue_ticket_post_idx on issue_ticket (post_id);
create index issue_ticket_due_date_idx on issue_ticket (due_date) where due_date is not null;

-- ADR 0014: connector outbox before Valkey publish (TEPP / orchestrator).
create table connector_outbox_event (
    outbox_event_id uuid primary key default uuid_generate_v4(),
    connector_code text not null
        references common_lookup_value (lookup_code),
    delivery_status_code text not null
        references common_lookup_value (lookup_code),
    idempotency_key text not null,
    payload_sha256 text not null,
    payload_json jsonb not null,
    stream_entry_id text,
    failure_code text,
    created_at timestamptz not null default now(),
    published_at timestamptz,
    unique (connector_code, idempotency_key)
);

create index connector_outbox_event_pending_idx
    on connector_outbox_event (delivery_status_code, created_at)
    where delivery_status_code = 'outbox_pending';

-- ---------------------------------------------------------------------
-- Post-to-post lineage: the persisted output of lineageweave.reconstruct
-- (see lineageweave/reconstruct.py -- this table is where a real
-- deployment would persist an Edge).
-- ---------------------------------------------------------------------
create table post_lineage_edge (
    parent_post_id uuid not null references source_post (post_id),
    child_post_id uuid not null references source_post (post_id),
    fused_score numeric not null,
    created_at timestamptz not null default now(),
    primary key (parent_post_id, child_post_id)
);

commit;

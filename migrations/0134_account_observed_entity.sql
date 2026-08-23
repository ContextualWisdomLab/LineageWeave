begin;

-- ADR 0144: an ADR-0010-created counterparty's verified ancestor chain
-- cannot reach an account's Customer Master view when the ancestor itself
-- was never directly mentioned in any post that account can read -- only
-- inferred as a parent from another account's private evidence. This
-- write-time, provenance-bearing link records the one ABAC predicate
-- read_customer_master already trusts, evaluated once at ingestion, so
-- no read-time catalog traversal (and its cross-account leak risk) is
-- ever needed to surface it.
create table if not exists account_observed_entity (
    account_id uuid not null references user_account (user_account_id) on delete cascade,
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id) on delete cascade,
    granting_corporate_entity_id uuid not null references corporate_entity (corporate_entity_id) on delete cascade,
    source_post_id uuid not null references source_post (post_id) on delete cascade,
    first_observed_at timestamptz not null default now(),
    last_observed_at timestamptz not null default now(),
    observation_count integer not null default 1 check (observation_count >= 1),
    primary key (account_id, corporate_entity_id)
);

create index if not exists account_observed_entity_granting_idx
    on account_observed_entity (granting_corporate_entity_id);

create index if not exists account_observed_entity_source_post_idx
    on account_observed_entity (source_post_id);

comment on table account_observed_entity is
    'ADR 0144: write-time record of which account observed which corporate_entity, through which of its own live affiliations, sourced from which post. Read-time joins back to account_affiliation on (account_id, granting_corporate_entity_id) so a revoked affiliation stops surfacing the entity with no reconciliation lag.';

commit;

-- API keys are an OIDC-account escape hatch for clients such as MCP tools.
-- Keyverse authenticates the account that creates/revokes a key; the raw key
-- never enters this database.
create table if not exists api_client_key (
    api_client_key_id uuid primary key default uuid_generate_v4(),
    user_account_id uuid not null references user_account (user_account_id) on delete cascade,
    key_name text not null check (length(btrim(key_name)) between 1 and 100),
    key_prefix text not null,
    secret_digest text not null unique check (secret_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    expires_at timestamptz,
    revoked_at timestamptz,
    check (revoked_at is null or revoked_at >= created_at),
    check (expires_at is null or expires_at > created_at)
);

create unique index if not exists api_client_key_active_name_idx
    on api_client_key (user_account_id, lower(key_name))
    where revoked_at is null;

create table if not exists api_client_key_scope (
    api_client_key_id uuid not null references api_client_key (api_client_key_id) on delete cascade,
    scope_code text not null check (scope_code in ('mcp:read')),
    primary key (api_client_key_id, scope_code)
);

create table if not exists api_client_key_event (
    api_client_key_event_id uuid primary key default uuid_generate_v4(),
    api_client_key_id uuid not null references api_client_key (api_client_key_id) on delete cascade,
    actor_user_account_id uuid not null references user_account (user_account_id) on delete cascade,
    event_code text not null check (event_code in ('issued', 'revoked')),
    occurred_at timestamptz not null default now()
);

create index if not exists api_client_key_user_idx
    on api_client_key (user_account_id, created_at desc);

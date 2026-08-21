-- ADR 0103: LineageWeave owns application-scoped MCP key material while
-- Keyverse remains the OIDC identity issuer and account authority.
create table if not exists mcp_api_key (
    mcp_api_key_id uuid primary key default gen_random_uuid(),
    user_account_id uuid not null references user_account(user_account_id) on delete cascade,
    display_name text not null check (char_length(btrim(display_name)) between 1 and 120),
    key_prefix text not null check (char_length(key_prefix) between 7 and 32),
    key_hash text not null unique check (char_length(key_hash) = 64),
    created_at timestamptz not null default now(),
    expires_at timestamptz,
    revoked_at timestamptz,
    check (expires_at is null or expires_at > created_at),
    check (revoked_at is null or revoked_at >= created_at)
);

create index if not exists mcp_api_key_user_account_idx
    on mcp_api_key (user_account_id, created_at desc);

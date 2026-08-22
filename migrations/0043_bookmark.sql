-- ADR 0063: a bookmark is an independently identifiable entity in 3NF.
-- Keep replay from recreating the legacy relation after ADR 0120 renames it.
do $$
begin
    if to_regclass('public.post_bookmark') is null then
        execute $table$
            create table if not exists bookmark (
                bookmark_id uuid primary key default gen_random_uuid(),
                user_account_id uuid not null references user_account(user_account_id) on delete cascade,
                post_id uuid not null references source_post(post_id) on delete cascade,
                created_at timestamptz not null default now(),
                unique (user_account_id, post_id)
            )
        $table$;
        execute $index$
            create index if not exists bookmark_post_idx on bookmark (post_id)
        $index$;
    end if;
end
$$;

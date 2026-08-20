-- ADR 0069: persist the member's Buyer locale on the member account.
alter table user_account
    add column if not exists preferred_locale text;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'user_account_preferred_locale_ck'
    ) then
        alter table user_account
            add constraint user_account_preferred_locale_ck
            check (preferred_locale is null or preferred_locale in ('en', 'ko', 'zh', 'ja', 'vi'));
    end if;
end $$;

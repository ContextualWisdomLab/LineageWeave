begin;

create table if not exists global_ask_exact_authorization_state (
    singleton boolean primary key default true check (singleton),
    authorization_version bigint not null check (authorization_version >= 0),
    changed_at timestamptz not null default now()
);

insert into global_ask_exact_authorization_state
    (singleton, authorization_version)
values (true, 0)
on conflict (singleton) do nothing;

create or replace function bump_global_ask_exact_authorization_version()
returns trigger
language plpgsql
as $$
begin
    update global_ask_exact_authorization_state
       set authorization_version = authorization_version + 1,
           changed_at = now()
     where singleton;
    return null;
end;
$$;

drop trigger if exists global_ask_exact_authorization_affiliation on account_affiliation;
create trigger global_ask_exact_authorization_affiliation
after insert or update or delete or truncate on account_affiliation
for each statement execute function bump_global_ask_exact_authorization_version();

drop trigger if exists global_ask_exact_authorization_assignment on account_role_assignment;
create trigger global_ask_exact_authorization_assignment
after insert or update or delete or truncate on account_role_assignment
for each statement execute function bump_global_ask_exact_authorization_version();

drop trigger if exists global_ask_exact_authorization_permission on role_permission;
create trigger global_ask_exact_authorization_permission
after insert or update or delete or truncate on role_permission
for each statement execute function bump_global_ask_exact_authorization_version();

drop trigger if exists global_ask_exact_authorization_process_unit on process_unit;
create trigger global_ask_exact_authorization_process_unit
after insert or update or delete or truncate on process_unit
for each statement execute function bump_global_ask_exact_authorization_version();

drop trigger if exists global_ask_exact_authorization_post on source_post;
create trigger global_ask_exact_authorization_post
after insert or update or delete or truncate on source_post
for each statement execute function bump_global_ask_exact_authorization_version();

commit;

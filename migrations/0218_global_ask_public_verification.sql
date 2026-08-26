-- Persist the reader's explicit public-verification opt-in with the Ask job.
-- The worker must not infer consent after the request has returned.

do $$
begin
    if exists (
        select 1
          from information_schema.columns
         where table_schema = 'public'
           and table_name = 'global_ask_job'
           and column_name = 'verify_external_requested'
           and (data_type <> 'boolean' or is_nullable <> 'NO')
    ) then
        raise exception 'global_ask_job.verify_external_requested has an incompatible shape';
    end if;
end $$;

alter table global_ask_job
    add column if not exists verify_external_requested boolean not null default false;

comment on column global_ask_job.verify_external_requested is
    'Reader opt-in captured at enqueue time; false never permits public claim egress.';

-- Persist the explicit as-of clock with the asynchronous Ask request.

do $$
begin
    if exists (
        select 1
          from information_schema.columns
         where table_schema = 'public'
           and table_name = 'global_ask_job'
           and column_name = 'knowledge_cutoff'
           and data_type <> 'timestamp with time zone'
    ) then
        raise exception 'global_ask_job.knowledge_cutoff has an incompatible shape';
    end if;
end $$;

alter table global_ask_job
    add column if not exists knowledge_cutoff timestamptz;

comment on column global_ask_job.knowledge_cutoff is
    'Optional requested evidence-availability cutoff for one Global Ask job.';

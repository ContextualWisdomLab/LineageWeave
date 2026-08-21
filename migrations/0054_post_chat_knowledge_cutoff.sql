alter table post_chat_result
    add column if not exists knowledge_cutoff timestamptz;

update post_chat_result
   set knowledge_cutoff = computed_at
 where knowledge_cutoff is null;

alter table post_chat_result
    alter column knowledge_cutoff set default now(),
    alter column knowledge_cutoff set not null;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_chat_result_knowledge_cutoff_check'
           and conrelid = 'post_chat_result'::regclass
    ) then
        alter table post_chat_result
            add constraint post_chat_result_knowledge_cutoff_check
            check (knowledge_cutoff <= computed_at);
    end if;
end
$$;

comment on column post_chat_result.knowledge_cutoff is
    'Maximum source availability time used to compute this persisted answer.';

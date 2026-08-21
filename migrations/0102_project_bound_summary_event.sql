alter table post_summary_event
    add column if not exists project_key text;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_summary_event_project_mention_fk'
           and conrelid = 'post_summary_event'::regclass
    ) then
        alter table post_summary_event
            add constraint post_summary_event_project_mention_fk
            foreign key (post_id, project_key)
            references post_project_mention (post_id, project_key);
    end if;
end
$$;

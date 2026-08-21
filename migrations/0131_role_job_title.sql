begin;

-- A person actor's stated title (PM, PRO, Sales Director, ...) is source
-- evidence distinct from what they did. Storing it only inside
-- responsibility_text left no way to render it separately, so the popup
-- showed a bare title standing in for a responsibility.
alter table post_summary_role add column if not exists job_title_text text;

comment on column post_summary_role.job_title_text is
    'Source-stated position/title for a person actor, kept separate from responsibility_text so a title is never mistaken for a concrete responsibility.';

commit;

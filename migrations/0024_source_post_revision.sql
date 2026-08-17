-- Store each source_post title/body rewrite as a dated revision (ADR 0025).
--
-- The analysis-run registry stays aggregates-only. Cutoff comparison
-- reads this source-layer history through GET /api/posts/{id}?as_of=.
-- A missing revision is omitted -- never a fabricated cutoff body.

begin;

create table if not exists source_post_revision (
    source_post_revision_id uuid primary key default uuid_generate_v4(),
    post_id uuid not null references source_post (post_id) on delete cascade,
    post_title text not null,
    post_body text not null,
    written_at timestamptz not null,
    superseded_at timestamptz,
    constraint source_post_revision_interval_check
        check (superseded_at is null or superseded_at >= written_at)
);

comment on table source_post_revision is
    'Valid-time title/body history for one source_post. Knowledge cutoffs '
    'stay on analysis_run; this table does not store a run id.';

comment on column source_post_revision.written_at is
    'When this title/body became current (ISO 8601 / W3C Time).';

comment on column source_post_revision.superseded_at is
    'When the next rewrite replaced this row. Null means current.';

create index if not exists source_post_revision_post_clock_idx
    on source_post_revision (post_id, written_at);

create unique index if not exists source_post_revision_current_idx
    on source_post_revision (post_id)
    where superseded_at is null;

create or replace function record_source_post_revision()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'UPDATE'
       and (new.post_title, new.post_body)
           is not distinct from (old.post_title, old.post_body) then
        return new;
    end if;
    if tg_op = 'UPDATE' then
        update source_post_revision
           set superseded_at = new.updated_at
         where post_id = new.post_id
           and superseded_at is null;
    end if;
    insert into source_post_revision (
        post_id, post_title, post_body, written_at
    ) values (
        new.post_id, new.post_title, new.post_body, new.updated_at
    );
    return new;
end;
$$;

comment on function record_source_post_revision() is
    'Writes a source_post_revision row on insert or title/body rewrite.';

drop trigger if exists source_post_revision_write on source_post;
create trigger source_post_revision_write
    after insert or update of post_title, post_body on source_post
    for each row
    execute function record_source_post_revision();

comment on trigger source_post_revision_write on source_post is
    'Keeps source_post_revision current when title or body changes (ADR 0025).';

insert into source_post_revision (post_id, post_title, post_body, written_at)
select post_id, post_title, post_body, updated_at
  from source_post sp
 where not exists (
           select 1
             from source_post_revision revision
            where revision.post_id = sp.post_id
       );

commit;

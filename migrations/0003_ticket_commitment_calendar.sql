-- Adds a due_date + LLM-authored commitment_summary to issue_ticket so a
-- ticket can double as a calendar/to-do entry (GET /api/calendar).
-- ADD COLUMN IF NOT EXISTS so a volume that already ran 0001 still upgrades.
-- due_date is a calendar date, not a timestamptz: a "by Friday" commitment
-- is a day, and binding a Python date into timestamptz midnight is an
-- off-by-one in any session whose TZ is not UTC.

alter table issue_ticket
    add column if not exists due_date date;

alter table issue_ticket
    add column if not exists commitment_summary text;

-- An earlier cut of this migration created timestamptz. Cast in place.
alter table issue_ticket
    alter column due_date type date using due_date::date;

create index if not exists issue_ticket_due_date_idx
    on issue_ticket (due_date) where due_date is not null;

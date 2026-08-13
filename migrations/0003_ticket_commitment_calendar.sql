-- Adds a due_date + LLM-authored commitment_summary to issue_ticket so a
-- ticket can double as a calendar/to-do entry (GET /api/calendar).
-- ADD COLUMN IF NOT EXISTS so a volume that already ran 0001 still upgrades.

alter table issue_ticket
    add column if not exists due_date timestamptz;

alter table issue_ticket
    add column if not exists commitment_summary text;

create index if not exists issue_ticket_due_date_idx
    on issue_ticket (due_date) where due_date is not null;

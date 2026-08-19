-- Same-name-people disambiguation signal: a stated job title/position is
-- real evidence a same person_name+person_side_code match is NOT the
-- same real individual. Lives on cataloged_person itself, not only
-- person_affiliation.role_title, because a title is real disambiguation
-- evidence even when the text names no specific organization to attach
-- an affiliation row to (e.g. "our legal counsel, Sam Okonkwo").
-- ADD COLUMN IF NOT EXISTS so a volume that already ran 0001 still
-- upgrades.

alter table cataloged_person
    add column if not exists last_known_job_title text;

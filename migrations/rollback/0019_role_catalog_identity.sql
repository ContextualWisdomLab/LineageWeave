-- Drop role-scoped catalog identity columns added by 0019.
-- Mention tables remain; only the role-row binding is removed.

alter table post_summary_role
    drop column if exists cataloged_team_id;

alter table post_summary_role
    drop column if exists cataloged_corporate_entity_id;

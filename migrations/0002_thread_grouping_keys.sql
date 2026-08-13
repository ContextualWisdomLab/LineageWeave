-- Persist reconstruct's group_key / secondary_key on source_post so
-- POST /api/lineage/rebuild can recover the designed A-100 fork.
-- ADD COLUMN IF NOT EXISTS so a volume that already ran 0001 still upgrades.

alter table source_post
    add column if not exists thread_group_key text not null default '';

alter table source_post
    add column if not exists secondary_grouping_key text not null default '';

-- Reverse migration 0021. source_post.updated_at remains a column;
-- only the rewrite trigger is removed.

begin;

drop trigger if exists source_post_write_clock on source_post;
drop function if exists touch_source_post_write_clock();

commit;

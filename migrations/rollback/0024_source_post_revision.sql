-- Reverse migration 0024. Live source_post rows stay; only revision
-- history and its write trigger are removed.

begin;

drop trigger if exists source_post_revision_write on source_post;
drop function if exists record_source_post_revision();
drop table if exists source_post_revision;

commit;

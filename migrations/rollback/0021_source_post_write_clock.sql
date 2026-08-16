-- Remove the live write-clock trigger. The updated_at column remains
-- on source_post from the initial schema.

drop trigger if exists source_post_set_updated_at on source_post;
drop function if exists set_source_post_updated_at();

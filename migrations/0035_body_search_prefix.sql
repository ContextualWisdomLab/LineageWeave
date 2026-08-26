-- Historical boundary retained for sorted replay. Migration 0036 supersedes
-- both original body indexes with image-safe normalized search indexes, so
-- recreating the obsolete indexes here would make every replay build and then
-- immediately drop two corpus-wide GIN indexes.
create extension if not exists pg_trgm;

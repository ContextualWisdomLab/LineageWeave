-- Roll back ADR 0053's bounded excerpt function after callers stop using it.
drop function if exists source_post_excerpt_text(text, integer);

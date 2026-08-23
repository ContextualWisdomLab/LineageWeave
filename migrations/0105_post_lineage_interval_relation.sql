-- ADR 0122: persist Allen (1983) interval relation on Event Lineage edges.
-- Lookups first so the FK can land on existing volumes that already ran 0001.

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('interval_relation', 'interval_before', 'Before', 0),
    ('interval_relation', 'interval_after', 'After', 1),
    ('interval_relation', 'interval_meets', 'Meets', 2),
    ('interval_relation', 'interval_met_by', 'Met by', 3),
    ('interval_relation', 'interval_overlaps', 'Overlaps', 4),
    ('interval_relation', 'interval_overlapped_by', 'Overlapped by', 5),
    ('interval_relation', 'interval_starts', 'Starts', 6),
    ('interval_relation', 'interval_started_by', 'Started by', 7),
    ('interval_relation', 'interval_during', 'During', 8),
    ('interval_relation', 'interval_contains', 'Contains', 9),
    ('interval_relation', 'interval_finishes', 'Finishes', 10),
    ('interval_relation', 'interval_finished_by', 'Finished by', 11),
    ('interval_relation', 'interval_equals', 'Equals', 12)
on conflict (lookup_code) do nothing;

alter table post_lineage_edge
    add column if not exists interval_relation_code text references common_lookup_value (lookup_code);

update post_lineage_edge as edge
   set interval_relation_code = case
        when parent_post.created_at::date < child_post.created_at::date then 'interval_before'
        when parent_post.created_at::date > child_post.created_at::date then 'interval_after'
        else 'interval_equals'
       end
  from source_post as parent_post
  join source_post as child_post on true
 where edge.parent_post_id = parent_post.post_id
   and edge.child_post_id = child_post.post_id
   and edge.interval_relation_code is null;

update post_lineage_edge
   set interval_relation_code = 'interval_before'
 where interval_relation_code is null;

do $$
begin
    if exists (
        select 1
          from information_schema.columns
         where table_name = 'post_lineage_edge'
           and column_name = 'interval_relation_code'
           and is_nullable = 'YES'
    ) then
        alter table post_lineage_edge
            alter column interval_relation_code set not null;
    end if;
end
$$;

delete from common_lookup_value lookup
where lookup.lookup_category = 'post_content_unit_kind'
  and lookup.lookup_code in
      ('paragraph', 'list', 'table', 'formula', 'conversation_turn')
  and not exists (
      select 1
        from post_content_unit unit
       where unit.unit_kind_code = lookup.lookup_code
  );

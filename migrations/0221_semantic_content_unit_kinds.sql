begin;

insert into common_lookup_value
    (lookup_category, lookup_code, lookup_label, display_order)
values
    ('post_content_unit_kind', 'paragraph', 'Paragraph', 3),
    ('post_content_unit_kind', 'list', 'List item', 4),
    ('post_content_unit_kind', 'table', 'Table row', 5),
    ('post_content_unit_kind', 'formula', 'Formula', 6),
    ('post_content_unit_kind', 'conversation_turn', 'Conversation turn', 7)
on conflict (lookup_code) do nothing;

commit;

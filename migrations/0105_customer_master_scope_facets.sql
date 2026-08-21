begin;

insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values
    ('account_affiliation_scope', 'scope_own_entity', 'Own company', 0),
    ('account_affiliation_scope', 'scope_granted_entity', 'Granted company', 1),
    ('account_affiliation_scope', 'scope_unclassified', 'Scope not classified', 2)
on conflict (lookup_code) do nothing;

alter table account_affiliation
    add column if not exists affiliation_scope_code text
        not null default 'scope_unclassified'
        references common_lookup_value (lookup_code);

create index if not exists account_affiliation_scope_idx
    on account_affiliation (user_account_id, affiliation_scope_code, corporate_entity_id);

commit;

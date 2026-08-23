-- ADR 0125 step 1: an explicit, nullable affiliation_scope_code so Customer
-- Master can eventually distinguish an account's own company from a
-- granted customer entity. This migration only adds the column and seeds
-- every existing row to scope_unclassified -- it does not infer own vs.
-- granted from a login token, a PU, a post title, or a corporate name, and
-- it does not change any authorization check. account_affiliation remains
-- the sole authorization source.
insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
    ('affiliation_scope', 'scope_own_entity', 'Own company', 0),
    ('affiliation_scope', 'scope_granted_entity', 'Granted customer entity', 1),
    ('affiliation_scope', 'scope_unclassified', 'Unclassified', 2)
on conflict (lookup_code) do nothing;

alter table account_affiliation
    add column if not exists affiliation_scope_code text
        default 'scope_unclassified'
        references common_lookup_value (lookup_code);

update account_affiliation
   set affiliation_scope_code = 'scope_unclassified'
 where affiliation_scope_code is null;

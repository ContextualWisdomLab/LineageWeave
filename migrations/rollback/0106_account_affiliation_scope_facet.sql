alter table account_affiliation drop column if exists affiliation_scope_code;
delete from common_lookup_value
 where lookup_category = 'affiliation_scope'
   and lookup_code in ('scope_own_entity', 'scope_granted_entity', 'scope_unclassified');

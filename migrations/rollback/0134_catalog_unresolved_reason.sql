alter table post_summary_role drop column if exists affiliation_catalog_unresolved_reason_code;
alter table post_summary_role drop column if exists catalog_unresolved_reason_code;
delete from common_lookup_value
 where lookup_category = 'catalog_unresolved_reason'
   and lookup_code in (
       'reason_tied_candidates',
       'reason_no_live_client',
       'reason_not_corroborated',
       'reason_no_catalog_entry'
   );

-- ADR 0272: unrelated account preferences must not rebuild every authored
-- Post's exact related-master search projection.
drop trigger if exists post_search_related_master_reconcile on user_account;
create trigger post_search_related_master_reconcile
after insert or delete or update of display_name, email_address
on user_account for each row
execute function reconcile_post_search_related_master();

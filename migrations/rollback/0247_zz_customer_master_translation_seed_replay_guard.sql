begin;

drop trigger if exists customer_master_seed_reviewed_text_replay_guard
    on ui_translation_text;
drop function if exists preserve_customer_master_reviewed_seed_text_on_replay();

commit;

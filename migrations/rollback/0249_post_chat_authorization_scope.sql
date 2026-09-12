drop trigger if exists invalidate_post_chat_replay_on_source_delete on source_post;
drop function if exists invalidate_post_chat_replay_on_source_post_delete();
drop table if exists post_chat_source;
drop table if exists post_chat_process_unit_scope;
drop table if exists post_chat_corporate_entity_scope;
drop table if exists post_chat_authorization_receipt;

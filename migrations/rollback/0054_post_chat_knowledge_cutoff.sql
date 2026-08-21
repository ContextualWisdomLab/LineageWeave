alter table post_chat_result
    drop constraint if exists post_chat_result_knowledge_cutoff_check;

alter table post_chat_result
    drop column if exists knowledge_cutoff;

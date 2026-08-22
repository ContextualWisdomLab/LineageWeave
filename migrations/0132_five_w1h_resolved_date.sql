begin;

-- A "when" EVIDENCE row keeps the post's own relative phrase (e.g. 올해 말,
-- 내년) in value_text, and may additionally carry that phrase resolved to an
-- absolute date using the post's authored date as the deictic anchor. The
-- phrase itself is never replaced; this column only adds a resolution.
alter table post_summary_five_w1h
    add column if not exists resolved_date_text text;

alter table post_summary_five_w1h
    drop constraint if exists post_summary_five_w1h_resolved_date_text_check;

alter table post_summary_five_w1h
    add constraint post_summary_five_w1h_resolved_date_text_check
    check (
        resolved_date_text is null
        or (
            slot_code = 'when'
            and resolved_date_text ~ '^\d{4}(-\d{2}(-\d{2})?)?$'
        )
    );

commit;

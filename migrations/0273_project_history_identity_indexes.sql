-- ADR 0243: exact Project History identity candidates must not scan the corpus.
create index if not exists source_post_project_code_identity_idx
    on source_post ((lower(btrim(normalize(coalesce(source_project_code, ''), NFKC),
                                 E' \t\n\r\f\v'))));

create index if not exists post_project_mention_key_identity_idx
    on post_project_mention ((lower(btrim(normalize(project_key, NFKC),
                                          E' \t\n\r\f\v'))));

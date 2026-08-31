-- ADR 0278: exact selected topic/context Rankings access paths.
create index if not exists topic_context_membership_selected_ranking_idx
    on topic_context_membership (
        topic_model_run_id, dimension_code, context_id,
        source_post_id, valid_from, valid_to
    );

create index if not exists topic_influence_selected_ranking_idx
    on topic_post_context_influence (
        topic_model_run_id, topic_influence_run_id, topic_index,
        influence_value desc, topic_context_membership_id
    ) include (uncertainty_lower_value, uncertainty_upper_value,
               uncertainty_method_code, diagnostic_status_code);

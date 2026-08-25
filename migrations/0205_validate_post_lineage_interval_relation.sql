-- Validate the ADR 0161 foreign key separately from its short NOT VALID installation.
alter table post_lineage_edge
    validate constraint post_lineage_edge_interval_relation_code_fkey;

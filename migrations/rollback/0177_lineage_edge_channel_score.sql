-- Roll back the per-channel lineage-edge score breakdown introduced by migration 0177.

drop table if exists post_lineage_edge_channel_score;

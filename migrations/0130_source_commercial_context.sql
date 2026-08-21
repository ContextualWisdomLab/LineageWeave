begin;

-- Preserve caller-mapped source evidence separately from resolved catalog
-- identity. The combination is computed at read/prompt time so omitted
-- source fields remain distinguishable from observed empty values.
alter table source_post add column if not exists source_order_pool_code text;
alter table source_post add column if not exists source_sales_order_code text;
alter table source_post add column if not exists source_sales_order_item_number bigint;
alter table source_post add column if not exists source_inspection_point_code text;

comment on column source_post.source_order_pool_code is
    'Raw source order-pool/project-pool code; presence is a lineage hint, not a resolved project or pool identity.';
comment on column source_post.source_sales_order_code is
    'Raw source sales-order code; absence is preserved and is not treated as proof that no order exists.';
comment on column source_post.source_sales_order_item_number is
    'Raw source sales-order item number; the source zero sentinel remains zero and is not changed to null.';
comment on column source_post.source_inspection_point_code is
    'Raw source inspection/status-point code; its meaning remains unresolved without a source codebook.';

create index if not exists source_post_order_pool_idx
    on source_post (source_order_pool_code)
    where nullif(btrim(source_order_pool_code), '') is not null;

create index if not exists source_post_sales_order_idx
    on source_post (source_sales_order_code)
    where nullif(btrim(source_sales_order_code), '') is not null;

commit;

begin;

-- Preserve caller-mapped names separately from codes and catalog identities.
alter table source_post add column if not exists source_sales_pool_name text;
alter table source_post add column if not exists source_customer_name text;
alter table source_post add column if not exists source_project_name text;

comment on column source_post.source_sales_pool_name is 'Raw source sales-pool name; a hint, not a resolved catalog identity.';
comment on column source_post.source_customer_name is 'Raw source customer name; unresolved names remain weak hints.';
comment on column source_post.source_project_name is 'Raw source project name; may be absent when the project is only described in text.';

commit;

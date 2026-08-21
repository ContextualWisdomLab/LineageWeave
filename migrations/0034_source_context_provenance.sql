begin;

-- Keep authorization scope separate from raw source identity and business
-- hints. These values are evidence inputs, not resolved catalog identities.
alter table source_post add column if not exists source_author_code text;
alter table source_post add column if not exists source_author_name text;
alter table source_post add column if not exists source_company_code text;
alter table source_post add column if not exists source_process_unit_code text;
alter table source_post add column if not exists source_sales_pool_code text;
alter table source_post add column if not exists source_customer_code text;
alter table source_post add column if not exists source_project_code text;

comment on column source_post.source_author_code is 'Raw source author/account code; not an authenticated product account.';
comment on column source_post.source_author_name is 'Raw source author name; not a cataloged person assertion.';
comment on column source_post.source_company_code is 'Raw source company code used as an ontology hint.';
comment on column source_post.source_process_unit_code is 'Raw source process-unit code used as an order-pool hint.';
comment on column source_post.source_sales_pool_code is 'Raw source sales-pool code used as an order-pool hint.';
comment on column source_post.source_customer_code is 'Raw source customer code; unresolved codes remain weak hints.';
comment on column source_post.source_project_code is 'Raw source project code; may be absent when the project is only described in text.';

commit;

begin;

alter table source_post
    add column if not exists source_company_name text;
alter table source_post
    add column if not exists source_process_unit_name text;

comment on column source_post.source_company_name is
    'Explicit company name from the source record; hint only until catalog resolution.';
comment on column source_post.source_process_unit_name is
    'Explicit PU/business-unit name from the source record; hint only, never a sales-pool mapping.';

commit;

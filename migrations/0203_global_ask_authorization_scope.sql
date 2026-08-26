-- Persist the exact authorization scope carried by the request token.

create table if not exists global_ask_job_corporate_entity_scope (
    global_ask_job_id uuid not null references global_ask_job (global_ask_job_id) on delete cascade,
    corporate_entity_id uuid not null references corporate_entity (corporate_entity_id),
    primary key (global_ask_job_id, corporate_entity_id)
);

create table if not exists global_ask_job_process_unit_scope (
    global_ask_job_id uuid not null references global_ask_job (global_ask_job_id) on delete cascade,
    process_unit_id uuid not null references process_unit (process_unit_id),
    primary key (global_ask_job_id, process_unit_id)
);

comment on table global_ask_job_corporate_entity_scope is
    'Corporate-entity authorization scope captured from the verified token when an Ask job is queued.';

comment on table global_ask_job_process_unit_scope is
    'Process-unit authorization scope captured from the verified token when an Ask job is queued.';

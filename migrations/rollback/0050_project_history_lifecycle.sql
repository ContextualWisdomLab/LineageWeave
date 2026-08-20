begin;

drop trigger if exists project_event_relation_scope_check on project_event_relation;
drop function if exists validate_project_event_relation_scope();
drop table if exists project_responsibility_assignment;
drop table if exists project_event_relation;
drop table if exists project_history_event;
drop table if exists project_history_project;

delete from common_lookup_value
 where lookup_code in (
    'project_event_order',
    'project_event_spec_change',
    'project_event_delivery',
    'project_event_voc',
    'project_event_rebid',
    'project_relation_follows',
    'project_relation_related_to',
    'project_relation_revises',
    'project_role_sales',
    'project_role_project_manager',
    'project_role_service'
 );

commit;

-- W3C PROV-O standards-complete provenance layer (ADR 0011).
--
-- Implements every one of the Recommendation's 30 classes and 50
-- normative object/datatype properties, both qualification tables, the
-- property/class hierarchies, and every Appendix B recommended inverse
-- name.  Runtime provenance data is stored separately from the product's
-- compact knowledge_graph_edge table because PROV-O must represent
-- literals and qualified Influence resources without flattening them.
--
-- All database objects use two-or-more-word snake_case and the catalog is
-- normalized: class/property definitions, hierarchies, domains, ranges,
-- qualification mappings, inverse names, resources, types, literals, and
-- assertions each have one authoritative table.

begin;

create table if not exists provenance_class_definition (
    class_code text primary key,
    class_iri text not null unique,
    class_local_name text not null unique,
    class_label text not null
);

create table if not exists provenance_class_hierarchy (
    child_class_code text not null references provenance_class_definition (class_code),
    parent_class_code text not null references provenance_class_definition (class_code),
    primary key (child_class_code, parent_class_code),
    check (child_class_code <> parent_class_code)
);

create table if not exists provenance_relation_definition (
    relation_code text primary key,
    relation_iri text not null unique,
    relation_local_name text not null unique,
    relation_label text not null,
    property_kind_code text not null check (property_kind_code in ('object', 'datatype')),
    datatype_iri text,
    symmetric_flag boolean not null default false,
    check (property_kind_code = 'datatype' or datatype_iri is null)
);

create table if not exists provenance_relation_hierarchy (
    child_relation_code text not null references provenance_relation_definition (relation_code),
    parent_relation_code text not null references provenance_relation_definition (relation_code),
    primary key (child_relation_code, parent_relation_code),
    check (child_relation_code <> parent_relation_code)
);

create table if not exists provenance_relation_domain (
    relation_code text not null references provenance_relation_definition (relation_code),
    domain_class_code text not null references provenance_class_definition (class_code),
    primary key (relation_code, domain_class_code)
);

create table if not exists provenance_relation_resource_range (
    relation_code text not null references provenance_relation_definition (relation_code),
    range_class_code text not null references provenance_class_definition (class_code),
    primary key (relation_code, range_class_code)
);

create table if not exists provenance_qualification_definition (
    unqualified_relation_code text primary key references provenance_relation_definition (relation_code),
    qualification_relation_code text not null unique references provenance_relation_definition (relation_code),
    influence_class_code text not null references provenance_class_definition (class_code),
    influencer_relation_code text not null references provenance_relation_definition (relation_code)
);

create table if not exists provenance_inverse_definition (
    relation_code text primary key references provenance_relation_definition (relation_code),
    inverse_local_name text not null,
    inverse_iri text not null,
    inverse_relation_code text references provenance_relation_definition (relation_code),
    inverse_kind_code text not null check (inverse_kind_code in ('defined', 'recommended')),
    check (
        (inverse_kind_code = 'defined' and inverse_relation_code is not null)
        or (inverse_kind_code = 'recommended' and inverse_relation_code is null)
    )
);

create table if not exists provenance_resource (
    resource_id uuid primary key default uuid_generate_v4(),
    resource_iri text not null unique,
    resource_label text,
    created_at timestamptz not null default now()
);

create table if not exists provenance_resource_type (
    resource_id uuid not null references provenance_resource (resource_id) on delete cascade,
    class_code text not null references provenance_class_definition (class_code),
    primary key (resource_id, class_code)
);

create table if not exists provenance_literal_value (
    literal_id uuid primary key default uuid_generate_v4(),
    lexical_value text not null,
    datatype_iri text,
    language_tag text,
    created_at timestamptz not null default now(),
    check (datatype_iri is null or language_tag is null)
);

create table if not exists provenance_resource_binding (
    resource_id uuid not null references provenance_resource (resource_id) on delete cascade,
    node_type_code text not null references common_lookup_value (lookup_code),
    node_id uuid not null,
    primary key (resource_id, node_type_code, node_id),
    unique (node_type_code, node_id)
);

create table if not exists provenance_assertion (
    assertion_id uuid primary key default uuid_generate_v4(),
    subject_resource_id uuid not null references provenance_resource (resource_id),
    relation_code text not null references provenance_relation_definition (relation_code),
    object_resource_id uuid references provenance_resource (resource_id),
    object_literal_id uuid references provenance_literal_value (literal_id),
    bundle_resource_id uuid references provenance_resource (resource_id),
    created_at timestamptz not null default now(),
    check (num_nonnulls(object_resource_id, object_literal_id) = 1)
);

create unique index if not exists provenance_assertion_resource_unique_idx
    on provenance_assertion (subject_resource_id, relation_code, object_resource_id, bundle_resource_id)
    nulls not distinct
    where object_resource_id is not null;

create unique index if not exists provenance_assertion_literal_unique_idx
    on provenance_assertion (subject_resource_id, relation_code, object_literal_id, bundle_resource_id)
    nulls not distinct
    where object_literal_id is not null;

create table if not exists provenance_assertion_derivation (
    derived_assertion_id uuid not null references provenance_assertion (assertion_id) on delete cascade,
    source_assertion_id uuid not null references provenance_assertion (assertion_id) on delete cascade,
    primary key (derived_assertion_id, source_assertion_id),
    check (derived_assertion_id <> source_assertion_id)
);

create or replace function validate_provenance_assertion_contract()
returns trigger
language plpgsql
as $$
declare
    relation_kind text;
    required_datatype text;
    literal_datatype text;
    literal_lexical text;
begin
    select property_kind_code, datatype_iri
      into relation_kind, required_datatype
      from provenance_relation_definition
     where relation_code = new.relation_code;

    if relation_kind = 'object' and new.object_resource_id is null then
        raise exception 'PROV-O object property % requires object_resource_id', new.relation_code;
    end if;
    if relation_kind = 'datatype' and new.object_literal_id is null then
        raise exception 'PROV-O datatype property % requires object_literal_id', new.relation_code;
    end if;

    if not exists (
        with recursive subject_class (class_code) as (
            select class_code
              from provenance_resource_type
             where resource_id = new.subject_resource_id
            union
            select hierarchy.parent_class_code
              from subject_class
              join provenance_class_hierarchy hierarchy
                on hierarchy.child_class_code = subject_class.class_code
        )
        select 1
          from subject_class
          join provenance_relation_domain domain_rule
            on domain_rule.domain_class_code = subject_class.class_code
         where domain_rule.relation_code = new.relation_code
    ) then
        raise exception 'subject resource % violates PROV-O domain for %',
            new.subject_resource_id, new.relation_code;
    end if;

    if relation_kind = 'object' and not exists (
        with recursive object_class (class_code) as (
            select class_code
              from provenance_resource_type
             where resource_id = new.object_resource_id
            union
            select hierarchy.parent_class_code
              from object_class
              join provenance_class_hierarchy hierarchy
                on hierarchy.child_class_code = object_class.class_code
        )
        select 1
          from object_class
          join provenance_relation_resource_range range_rule
            on range_rule.range_class_code = object_class.class_code
         where range_rule.relation_code = new.relation_code
    ) then
        raise exception 'object resource % violates PROV-O range for %',
            new.object_resource_id, new.relation_code;
    end if;

    if relation_kind = 'datatype' then
        select datatype_iri, lexical_value
          into literal_datatype, literal_lexical
          from provenance_literal_value
         where literal_id = new.object_literal_id;

        if required_datatype is not null
           and literal_datatype is distinct from required_datatype then
            raise exception 'literal % violates datatype % for %',
                new.object_literal_id, required_datatype, new.relation_code;
        end if;

        if required_datatype = 'http://www.w3.org/2001/XMLSchema#dateTime' then
            if literal_lexical !~ (
                '^[0-9]{4}-(0[1-9]|1[0-2])-'
                '(0[1-9]|[12][0-9]|3[01])T'
                '([01][0-9]|2[0-3]):[0-5][0-9]:'
                '[0-5][0-9](\.[0-9]+)?'
                '(Z|[+-](0[0-9]|1[0-4]):[0-5][0-9])$'
            ) then
                raise exception 'literal % violates lexical xsd:dateTime for %',
                    new.object_literal_id, new.relation_code;
            end if;
            begin
                perform literal_lexical::timestamptz;
            exception when others then
                raise exception 'literal % violates lexical xsd:dateTime for %',
                    new.object_literal_id, new.relation_code;
            end;
        end if;
    end if;

    return new;
end;
$$;

drop trigger if exists provenance_assertion_contract_trigger on provenance_assertion;
create trigger provenance_assertion_contract_trigger
before insert or update on provenance_assertion
for each row execute function validate_provenance_assertion_contract();

create or replace function protect_provenance_contract_reference()
returns trigger
language plpgsql
as $$
begin
    if tg_table_name = 'provenance_resource_type' and exists (
        select 1
          from provenance_assertion
         where subject_resource_id = (to_jsonb(old)->>'resource_id')::uuid
            or object_resource_id = (to_jsonb(old)->>'resource_id')::uuid
    ) then
        raise exception 'referenced provenance resource types are immutable';
    end if;

    if tg_table_name = 'provenance_literal_value' and exists (
        select 1
          from provenance_assertion
         where object_literal_id = (to_jsonb(old)->>'literal_id')::uuid
    ) then
        raise exception 'referenced provenance literal values are immutable';
    end if;
    if tg_op = 'UPDATE' then
        return new;
    end if;
    return old;
end;
$$;

drop trigger if exists provenance_resource_type_reference_trigger
    on provenance_resource_type;
create trigger provenance_resource_type_reference_trigger
before update or delete on provenance_resource_type
for each row execute function protect_provenance_contract_reference();

drop trigger if exists provenance_literal_value_reference_trigger
    on provenance_literal_value;
create trigger provenance_literal_value_reference_trigger
before update or delete on provenance_literal_value
for each row execute function protect_provenance_contract_reference();

insert into provenance_class_definition (class_code, class_iri, class_local_name, class_label) values
    ('prov_entity', 'http://www.w3.org/ns/prov#Entity', 'Entity', 'Entity'),
    ('prov_activity', 'http://www.w3.org/ns/prov#Activity', 'Activity', 'Activity'),
    ('prov_agent', 'http://www.w3.org/ns/prov#Agent', 'Agent', 'Agent'),
    ('prov_collection', 'http://www.w3.org/ns/prov#Collection', 'Collection', 'Collection'),
    ('prov_empty_collection', 'http://www.w3.org/ns/prov#EmptyCollection', 'EmptyCollection', 'Empty Collection'),
    ('prov_bundle', 'http://www.w3.org/ns/prov#Bundle', 'Bundle', 'Bundle'),
    ('prov_person', 'http://www.w3.org/ns/prov#Person', 'Person', 'Person'),
    ('prov_software_agent', 'http://www.w3.org/ns/prov#SoftwareAgent', 'SoftwareAgent', 'Software Agent'),
    ('prov_organization', 'http://www.w3.org/ns/prov#Organization', 'Organization', 'Organization'),
    ('prov_location', 'http://www.w3.org/ns/prov#Location', 'Location', 'Location'),
    ('prov_influence', 'http://www.w3.org/ns/prov#Influence', 'Influence', 'Influence'),
    ('prov_entity_influence', 'http://www.w3.org/ns/prov#EntityInfluence', 'EntityInfluence', 'Entity Influence'),
    ('prov_usage', 'http://www.w3.org/ns/prov#Usage', 'Usage', 'Usage'),
    ('prov_start', 'http://www.w3.org/ns/prov#Start', 'Start', 'Start'),
    ('prov_end', 'http://www.w3.org/ns/prov#End', 'End', 'End'),
    ('prov_derivation', 'http://www.w3.org/ns/prov#Derivation', 'Derivation', 'Derivation'),
    ('prov_primary_source', 'http://www.w3.org/ns/prov#PrimarySource', 'PrimarySource', 'Primary Source'),
    ('prov_quotation', 'http://www.w3.org/ns/prov#Quotation', 'Quotation', 'Quotation'),
    ('prov_revision', 'http://www.w3.org/ns/prov#Revision', 'Revision', 'Revision'),
    ('prov_activity_influence', 'http://www.w3.org/ns/prov#ActivityInfluence', 'ActivityInfluence', 'Activity Influence'),
    ('prov_generation', 'http://www.w3.org/ns/prov#Generation', 'Generation', 'Generation'),
    ('prov_communication', 'http://www.w3.org/ns/prov#Communication', 'Communication', 'Communication'),
    ('prov_invalidation', 'http://www.w3.org/ns/prov#Invalidation', 'Invalidation', 'Invalidation'),
    ('prov_agent_influence', 'http://www.w3.org/ns/prov#AgentInfluence', 'AgentInfluence', 'Agent Influence'),
    ('prov_attribution', 'http://www.w3.org/ns/prov#Attribution', 'Attribution', 'Attribution'),
    ('prov_association', 'http://www.w3.org/ns/prov#Association', 'Association', 'Association'),
    ('prov_plan', 'http://www.w3.org/ns/prov#Plan', 'Plan', 'Plan'),
    ('prov_delegation', 'http://www.w3.org/ns/prov#Delegation', 'Delegation', 'Delegation'),
    ('prov_instantaneous_event', 'http://www.w3.org/ns/prov#InstantaneousEvent', 'InstantaneousEvent', 'Instantaneous Event'),
    ('prov_role', 'http://www.w3.org/ns/prov#Role', 'Role', 'Role')
on conflict (class_code) do update set
    class_iri = excluded.class_iri,
    class_local_name = excluded.class_local_name,
    class_label = excluded.class_label;

insert into provenance_class_hierarchy (child_class_code, parent_class_code) values
    ('prov_collection', 'prov_entity'),
    ('prov_empty_collection', 'prov_collection'),
    ('prov_bundle', 'prov_entity'),
    ('prov_person', 'prov_agent'),
    ('prov_software_agent', 'prov_agent'),
    ('prov_organization', 'prov_agent'),
    ('prov_entity_influence', 'prov_influence'),
    ('prov_usage', 'prov_instantaneous_event'),
    ('prov_usage', 'prov_entity_influence'),
    ('prov_start', 'prov_instantaneous_event'),
    ('prov_start', 'prov_entity_influence'),
    ('prov_end', 'prov_instantaneous_event'),
    ('prov_end', 'prov_entity_influence'),
    ('prov_derivation', 'prov_entity_influence'),
    ('prov_primary_source', 'prov_derivation'),
    ('prov_quotation', 'prov_derivation'),
    ('prov_revision', 'prov_derivation'),
    ('prov_activity_influence', 'prov_influence'),
    ('prov_generation', 'prov_instantaneous_event'),
    ('prov_generation', 'prov_activity_influence'),
    ('prov_communication', 'prov_activity_influence'),
    ('prov_invalidation', 'prov_instantaneous_event'),
    ('prov_invalidation', 'prov_activity_influence'),
    ('prov_agent_influence', 'prov_influence'),
    ('prov_attribution', 'prov_agent_influence'),
    ('prov_association', 'prov_agent_influence'),
    ('prov_plan', 'prov_entity'),
    ('prov_delegation', 'prov_agent_influence')
on conflict do nothing;

insert into provenance_relation_definition (relation_code, relation_iri, relation_local_name, relation_label, property_kind_code, datatype_iri, symmetric_flag) values
    ('prov_was_generated_by', 'http://www.w3.org/ns/prov#wasGeneratedBy', 'wasGeneratedBy', 'Was Generated By', 'object', null, false),
    ('prov_was_derived_from', 'http://www.w3.org/ns/prov#wasDerivedFrom', 'wasDerivedFrom', 'Was Derived From', 'object', null, false),
    ('prov_was_attributed_to', 'http://www.w3.org/ns/prov#wasAttributedTo', 'wasAttributedTo', 'Was Attributed To', 'object', null, false),
    ('prov_started_at_time', 'http://www.w3.org/ns/prov#startedAtTime', 'startedAtTime', 'Started At Time', 'datatype', 'http://www.w3.org/2001/XMLSchema#dateTime', false),
    ('prov_used', 'http://www.w3.org/ns/prov#used', 'used', 'Used', 'object', null, false),
    ('prov_was_informed_by', 'http://www.w3.org/ns/prov#wasInformedBy', 'wasInformedBy', 'Was Informed By', 'object', null, false),
    ('prov_ended_at_time', 'http://www.w3.org/ns/prov#endedAtTime', 'endedAtTime', 'Ended At Time', 'datatype', 'http://www.w3.org/2001/XMLSchema#dateTime', false),
    ('prov_was_associated_with', 'http://www.w3.org/ns/prov#wasAssociatedWith', 'wasAssociatedWith', 'Was Associated With', 'object', null, false),
    ('prov_acted_on_behalf_of', 'http://www.w3.org/ns/prov#actedOnBehalfOf', 'actedOnBehalfOf', 'Acted On Behalf Of', 'object', null, false),
    ('prov_alternate_of', 'http://www.w3.org/ns/prov#alternateOf', 'alternateOf', 'Alternate Of', 'object', null, true),
    ('prov_specialization_of', 'http://www.w3.org/ns/prov#specializationOf', 'specializationOf', 'Specialization Of', 'object', null, false),
    ('prov_generated_at_time', 'http://www.w3.org/ns/prov#generatedAtTime', 'generatedAtTime', 'Generated At Time', 'datatype', 'http://www.w3.org/2001/XMLSchema#dateTime', false),
    ('prov_had_primary_source', 'http://www.w3.org/ns/prov#hadPrimarySource', 'hadPrimarySource', 'Had Primary Source', 'object', null, false),
    ('prov_value', 'http://www.w3.org/ns/prov#value', 'value', 'Value', 'datatype', null, false),
    ('prov_was_quoted_from', 'http://www.w3.org/ns/prov#wasQuotedFrom', 'wasQuotedFrom', 'Was Quoted From', 'object', null, false),
    ('prov_was_revision_of', 'http://www.w3.org/ns/prov#wasRevisionOf', 'wasRevisionOf', 'Was Revision Of', 'object', null, false),
    ('prov_invalidated_at_time', 'http://www.w3.org/ns/prov#invalidatedAtTime', 'invalidatedAtTime', 'Invalidated At Time', 'datatype', 'http://www.w3.org/2001/XMLSchema#dateTime', false),
    ('prov_was_invalidated_by', 'http://www.w3.org/ns/prov#wasInvalidatedBy', 'wasInvalidatedBy', 'Was Invalidated By', 'object', null, false),
    ('prov_had_member', 'http://www.w3.org/ns/prov#hadMember', 'hadMember', 'Had Member', 'object', null, false),
    ('prov_was_started_by', 'http://www.w3.org/ns/prov#wasStartedBy', 'wasStartedBy', 'Was Started By', 'object', null, false),
    ('prov_was_ended_by', 'http://www.w3.org/ns/prov#wasEndedBy', 'wasEndedBy', 'Was Ended By', 'object', null, false),
    ('prov_invalidated', 'http://www.w3.org/ns/prov#invalidated', 'invalidated', 'Invalidated', 'object', null, false),
    ('prov_influenced', 'http://www.w3.org/ns/prov#influenced', 'influenced', 'Influenced', 'object', null, false),
    ('prov_at_location', 'http://www.w3.org/ns/prov#atLocation', 'atLocation', 'At Location', 'object', null, false),
    ('prov_generated', 'http://www.w3.org/ns/prov#generated', 'generated', 'Generated', 'object', null, false),
    ('prov_was_influenced_by', 'http://www.w3.org/ns/prov#wasInfluencedBy', 'wasInfluencedBy', 'Was Influenced By', 'object', null, false),
    ('prov_qualified_influence', 'http://www.w3.org/ns/prov#qualifiedInfluence', 'qualifiedInfluence', 'Qualified Influence', 'object', null, false),
    ('prov_qualified_generation', 'http://www.w3.org/ns/prov#qualifiedGeneration', 'qualifiedGeneration', 'Qualified Generation', 'object', null, false),
    ('prov_qualified_derivation', 'http://www.w3.org/ns/prov#qualifiedDerivation', 'qualifiedDerivation', 'Qualified Derivation', 'object', null, false),
    ('prov_qualified_primary_source', 'http://www.w3.org/ns/prov#qualifiedPrimarySource', 'qualifiedPrimarySource', 'Qualified Primary Source', 'object', null, false),
    ('prov_qualified_quotation', 'http://www.w3.org/ns/prov#qualifiedQuotation', 'qualifiedQuotation', 'Qualified Quotation', 'object', null, false),
    ('prov_qualified_revision', 'http://www.w3.org/ns/prov#qualifiedRevision', 'qualifiedRevision', 'Qualified Revision', 'object', null, false),
    ('prov_qualified_attribution', 'http://www.w3.org/ns/prov#qualifiedAttribution', 'qualifiedAttribution', 'Qualified Attribution', 'object', null, false),
    ('prov_qualified_invalidation', 'http://www.w3.org/ns/prov#qualifiedInvalidation', 'qualifiedInvalidation', 'Qualified Invalidation', 'object', null, false),
    ('prov_qualified_start', 'http://www.w3.org/ns/prov#qualifiedStart', 'qualifiedStart', 'Qualified Start', 'object', null, false),
    ('prov_qualified_usage', 'http://www.w3.org/ns/prov#qualifiedUsage', 'qualifiedUsage', 'Qualified Usage', 'object', null, false),
    ('prov_qualified_communication', 'http://www.w3.org/ns/prov#qualifiedCommunication', 'qualifiedCommunication', 'Qualified Communication', 'object', null, false),
    ('prov_qualified_association', 'http://www.w3.org/ns/prov#qualifiedAssociation', 'qualifiedAssociation', 'Qualified Association', 'object', null, false),
    ('prov_qualified_end', 'http://www.w3.org/ns/prov#qualifiedEnd', 'qualifiedEnd', 'Qualified End', 'object', null, false),
    ('prov_qualified_delegation', 'http://www.w3.org/ns/prov#qualifiedDelegation', 'qualifiedDelegation', 'Qualified Delegation', 'object', null, false),
    ('prov_influencer', 'http://www.w3.org/ns/prov#influencer', 'influencer', 'Influencer', 'object', null, false),
    ('prov_entity', 'http://www.w3.org/ns/prov#entity', 'entity', 'Entity', 'object', null, false),
    ('prov_had_usage', 'http://www.w3.org/ns/prov#hadUsage', 'hadUsage', 'Had Usage', 'object', null, false),
    ('prov_had_generation', 'http://www.w3.org/ns/prov#hadGeneration', 'hadGeneration', 'Had Generation', 'object', null, false),
    ('prov_activity', 'http://www.w3.org/ns/prov#activity', 'activity', 'Activity', 'object', null, false),
    ('prov_agent', 'http://www.w3.org/ns/prov#agent', 'agent', 'Agent', 'object', null, false),
    ('prov_had_plan', 'http://www.w3.org/ns/prov#hadPlan', 'hadPlan', 'Had Plan', 'object', null, false),
    ('prov_had_activity', 'http://www.w3.org/ns/prov#hadActivity', 'hadActivity', 'Had Activity', 'object', null, false),
    ('prov_at_time', 'http://www.w3.org/ns/prov#atTime', 'atTime', 'At Time', 'datatype', 'http://www.w3.org/2001/XMLSchema#dateTime', false),
    ('prov_had_role', 'http://www.w3.org/ns/prov#hadRole', 'hadRole', 'Had Role', 'object', null, false)
on conflict (relation_code) do update set
    relation_iri = excluded.relation_iri,
    relation_local_name = excluded.relation_local_name,
    relation_label = excluded.relation_label,
    property_kind_code = excluded.property_kind_code,
    datatype_iri = excluded.datatype_iri,
    symmetric_flag = excluded.symmetric_flag;

insert into provenance_relation_hierarchy (child_relation_code, parent_relation_code) values
    ('prov_was_generated_by', 'prov_was_influenced_by'),
    ('prov_was_derived_from', 'prov_was_influenced_by'),
    ('prov_was_attributed_to', 'prov_was_influenced_by'),
    ('prov_used', 'prov_was_influenced_by'),
    ('prov_was_informed_by', 'prov_was_influenced_by'),
    ('prov_was_associated_with', 'prov_was_influenced_by'),
    ('prov_acted_on_behalf_of', 'prov_was_influenced_by'),
    ('prov_specialization_of', 'prov_alternate_of'),
    ('prov_had_primary_source', 'prov_was_derived_from'),
    ('prov_was_quoted_from', 'prov_was_derived_from'),
    ('prov_was_revision_of', 'prov_was_derived_from'),
    ('prov_was_invalidated_by', 'prov_was_influenced_by'),
    ('prov_had_member', 'prov_was_influenced_by'),
    ('prov_was_started_by', 'prov_was_influenced_by'),
    ('prov_was_ended_by', 'prov_was_influenced_by'),
    ('prov_invalidated', 'prov_influenced'),
    ('prov_generated', 'prov_influenced'),
    ('prov_qualified_generation', 'prov_qualified_influence'),
    ('prov_qualified_derivation', 'prov_qualified_influence'),
    ('prov_qualified_primary_source', 'prov_qualified_influence'),
    ('prov_qualified_quotation', 'prov_qualified_influence'),
    ('prov_qualified_revision', 'prov_qualified_influence'),
    ('prov_qualified_attribution', 'prov_qualified_influence'),
    ('prov_qualified_invalidation', 'prov_qualified_influence'),
    ('prov_qualified_start', 'prov_qualified_influence'),
    ('prov_qualified_usage', 'prov_qualified_influence'),
    ('prov_qualified_communication', 'prov_qualified_influence'),
    ('prov_qualified_association', 'prov_qualified_influence'),
    ('prov_qualified_end', 'prov_qualified_influence'),
    ('prov_qualified_delegation', 'prov_qualified_influence'),
    ('prov_entity', 'prov_influencer'),
    ('prov_activity', 'prov_influencer'),
    ('prov_agent', 'prov_influencer')
on conflict do nothing;

insert into provenance_relation_domain (relation_code, domain_class_code) values
    ('prov_was_generated_by', 'prov_entity'),
    ('prov_was_derived_from', 'prov_entity'),
    ('prov_was_attributed_to', 'prov_entity'),
    ('prov_started_at_time', 'prov_activity'),
    ('prov_used', 'prov_activity'),
    ('prov_was_informed_by', 'prov_activity'),
    ('prov_ended_at_time', 'prov_activity'),
    ('prov_was_associated_with', 'prov_activity'),
    ('prov_acted_on_behalf_of', 'prov_agent'),
    ('prov_alternate_of', 'prov_entity'),
    ('prov_specialization_of', 'prov_entity'),
    ('prov_generated_at_time', 'prov_entity'),
    ('prov_had_primary_source', 'prov_entity'),
    ('prov_value', 'prov_entity'),
    ('prov_was_quoted_from', 'prov_entity'),
    ('prov_was_revision_of', 'prov_entity'),
    ('prov_invalidated_at_time', 'prov_entity'),
    ('prov_was_invalidated_by', 'prov_entity'),
    ('prov_had_member', 'prov_collection'),
    ('prov_was_started_by', 'prov_activity'),
    ('prov_was_ended_by', 'prov_activity'),
    ('prov_invalidated', 'prov_activity'),
    ('prov_influenced', 'prov_entity'),
    ('prov_influenced', 'prov_activity'),
    ('prov_influenced', 'prov_agent'),
    ('prov_at_location', 'prov_activity'),
    ('prov_at_location', 'prov_agent'),
    ('prov_at_location', 'prov_entity'),
    ('prov_at_location', 'prov_instantaneous_event'),
    ('prov_generated', 'prov_activity'),
    ('prov_was_influenced_by', 'prov_entity'),
    ('prov_was_influenced_by', 'prov_activity'),
    ('prov_was_influenced_by', 'prov_agent'),
    ('prov_qualified_influence', 'prov_entity'),
    ('prov_qualified_influence', 'prov_activity'),
    ('prov_qualified_influence', 'prov_agent'),
    ('prov_qualified_generation', 'prov_entity'),
    ('prov_qualified_derivation', 'prov_entity'),
    ('prov_qualified_primary_source', 'prov_entity'),
    ('prov_qualified_quotation', 'prov_entity'),
    ('prov_qualified_revision', 'prov_entity'),
    ('prov_qualified_attribution', 'prov_entity'),
    ('prov_qualified_invalidation', 'prov_entity'),
    ('prov_qualified_start', 'prov_activity'),
    ('prov_qualified_usage', 'prov_activity'),
    ('prov_qualified_communication', 'prov_activity'),
    ('prov_qualified_association', 'prov_activity'),
    ('prov_qualified_end', 'prov_activity'),
    ('prov_qualified_delegation', 'prov_agent'),
    ('prov_influencer', 'prov_influence'),
    ('prov_entity', 'prov_entity_influence'),
    ('prov_had_usage', 'prov_derivation'),
    ('prov_had_generation', 'prov_derivation'),
    ('prov_activity', 'prov_activity_influence'),
    ('prov_agent', 'prov_agent_influence'),
    ('prov_had_plan', 'prov_association'),
    ('prov_had_activity', 'prov_delegation'),
    ('prov_had_activity', 'prov_derivation'),
    ('prov_had_activity', 'prov_end'),
    ('prov_had_activity', 'prov_start'),
    ('prov_at_time', 'prov_instantaneous_event'),
    ('prov_had_role', 'prov_association'),
    ('prov_had_role', 'prov_instantaneous_event')
on conflict do nothing;

insert into provenance_relation_resource_range (relation_code, range_class_code) values
    ('prov_was_generated_by', 'prov_activity'),
    ('prov_was_derived_from', 'prov_entity'),
    ('prov_was_attributed_to', 'prov_agent'),
    ('prov_used', 'prov_entity'),
    ('prov_was_informed_by', 'prov_activity'),
    ('prov_was_associated_with', 'prov_agent'),
    ('prov_acted_on_behalf_of', 'prov_agent'),
    ('prov_alternate_of', 'prov_entity'),
    ('prov_specialization_of', 'prov_entity'),
    ('prov_had_primary_source', 'prov_entity'),
    ('prov_was_quoted_from', 'prov_entity'),
    ('prov_was_revision_of', 'prov_entity'),
    ('prov_was_invalidated_by', 'prov_activity'),
    ('prov_had_member', 'prov_entity'),
    ('prov_was_started_by', 'prov_entity'),
    ('prov_was_ended_by', 'prov_entity'),
    ('prov_invalidated', 'prov_entity'),
    ('prov_influenced', 'prov_entity'),
    ('prov_influenced', 'prov_activity'),
    ('prov_influenced', 'prov_agent'),
    ('prov_at_location', 'prov_location'),
    ('prov_generated', 'prov_entity'),
    ('prov_was_influenced_by', 'prov_entity'),
    ('prov_was_influenced_by', 'prov_activity'),
    ('prov_was_influenced_by', 'prov_agent'),
    ('prov_qualified_influence', 'prov_influence'),
    ('prov_qualified_generation', 'prov_generation'),
    ('prov_qualified_derivation', 'prov_derivation'),
    ('prov_qualified_primary_source', 'prov_primary_source'),
    ('prov_qualified_quotation', 'prov_quotation'),
    ('prov_qualified_revision', 'prov_revision'),
    ('prov_qualified_attribution', 'prov_attribution'),
    ('prov_qualified_invalidation', 'prov_invalidation'),
    ('prov_qualified_start', 'prov_start'),
    ('prov_qualified_usage', 'prov_usage'),
    ('prov_qualified_communication', 'prov_communication'),
    ('prov_qualified_association', 'prov_association'),
    ('prov_qualified_end', 'prov_end'),
    ('prov_qualified_delegation', 'prov_delegation'),
    ('prov_influencer', 'prov_entity'),
    ('prov_influencer', 'prov_activity'),
    ('prov_influencer', 'prov_agent'),
    ('prov_entity', 'prov_entity'),
    ('prov_had_usage', 'prov_usage'),
    ('prov_had_generation', 'prov_generation'),
    ('prov_activity', 'prov_activity'),
    ('prov_agent', 'prov_agent'),
    ('prov_had_plan', 'prov_plan'),
    ('prov_had_activity', 'prov_activity'),
    ('prov_had_role', 'prov_role')
on conflict do nothing;

insert into provenance_qualification_definition (unqualified_relation_code, qualification_relation_code, influence_class_code, influencer_relation_code) values
    ('prov_was_generated_by', 'prov_qualified_generation', 'prov_generation', 'prov_activity'),
    ('prov_was_derived_from', 'prov_qualified_derivation', 'prov_derivation', 'prov_entity'),
    ('prov_was_attributed_to', 'prov_qualified_attribution', 'prov_attribution', 'prov_agent'),
    ('prov_used', 'prov_qualified_usage', 'prov_usage', 'prov_entity'),
    ('prov_was_informed_by', 'prov_qualified_communication', 'prov_communication', 'prov_activity'),
    ('prov_was_associated_with', 'prov_qualified_association', 'prov_association', 'prov_agent'),
    ('prov_acted_on_behalf_of', 'prov_qualified_delegation', 'prov_delegation', 'prov_agent'),
    ('prov_was_influenced_by', 'prov_qualified_influence', 'prov_influence', 'prov_influencer'),
    ('prov_had_primary_source', 'prov_qualified_primary_source', 'prov_primary_source', 'prov_entity'),
    ('prov_was_quoted_from', 'prov_qualified_quotation', 'prov_quotation', 'prov_entity'),
    ('prov_was_revision_of', 'prov_qualified_revision', 'prov_revision', 'prov_entity'),
    ('prov_was_invalidated_by', 'prov_qualified_invalidation', 'prov_invalidation', 'prov_activity'),
    ('prov_was_started_by', 'prov_qualified_start', 'prov_start', 'prov_entity'),
    ('prov_was_ended_by', 'prov_qualified_end', 'prov_end', 'prov_entity')
on conflict (unqualified_relation_code) do update set
    qualification_relation_code = excluded.qualification_relation_code,
    influence_class_code = excluded.influence_class_code,
    influencer_relation_code = excluded.influencer_relation_code;

insert into provenance_inverse_definition (relation_code, inverse_local_name, inverse_iri, inverse_relation_code, inverse_kind_code) values
    ('prov_acted_on_behalf_of', 'hadDelegate', 'http://www.w3.org/ns/prov#hadDelegate', null, 'recommended'),
    ('prov_activity', 'activityOfInfluence', 'http://www.w3.org/ns/prov#activityOfInfluence', null, 'recommended'),
    ('prov_agent', 'agentOfInfluence', 'http://www.w3.org/ns/prov#agentOfInfluence', null, 'recommended'),
    ('prov_alternate_of', 'alternateOf', 'http://www.w3.org/ns/prov#alternateOf', 'prov_alternate_of', 'defined'),
    ('prov_at_location', 'locationOf', 'http://www.w3.org/ns/prov#locationOf', null, 'recommended'),
    ('prov_entity', 'entityOfInfluence', 'http://www.w3.org/ns/prov#entityOfInfluence', null, 'recommended'),
    ('prov_generated', 'wasGeneratedBy', 'http://www.w3.org/ns/prov#wasGeneratedBy', 'prov_was_generated_by', 'defined'),
    ('prov_had_activity', 'wasActivityOfInfluence', 'http://www.w3.org/ns/prov#wasActivityOfInfluence', null, 'recommended'),
    ('prov_had_generation', 'generatedAsDerivation', 'http://www.w3.org/ns/prov#generatedAsDerivation', null, 'recommended'),
    ('prov_had_member', 'wasMemberOf', 'http://www.w3.org/ns/prov#wasMemberOf', null, 'recommended'),
    ('prov_had_plan', 'wasPlanOf', 'http://www.w3.org/ns/prov#wasPlanOf', null, 'recommended'),
    ('prov_had_primary_source', 'wasPrimarySourceOf', 'http://www.w3.org/ns/prov#wasPrimarySourceOf', null, 'recommended'),
    ('prov_had_role', 'wasRoleIn', 'http://www.w3.org/ns/prov#wasRoleIn', null, 'recommended'),
    ('prov_had_usage', 'wasUsedInDerivation', 'http://www.w3.org/ns/prov#wasUsedInDerivation', null, 'recommended'),
    ('prov_influenced', 'wasInfluencedBy', 'http://www.w3.org/ns/prov#wasInfluencedBy', 'prov_was_influenced_by', 'defined'),
    ('prov_influencer', 'hadInfluence', 'http://www.w3.org/ns/prov#hadInfluence', null, 'recommended'),
    ('prov_invalidated', 'wasInvalidatedBy', 'http://www.w3.org/ns/prov#wasInvalidatedBy', 'prov_was_invalidated_by', 'defined'),
    ('prov_qualified_association', 'qualifiedAssociationOf', 'http://www.w3.org/ns/prov#qualifiedAssociationOf', null, 'recommended'),
    ('prov_qualified_attribution', 'qualifiedAttributionOf', 'http://www.w3.org/ns/prov#qualifiedAttributionOf', null, 'recommended'),
    ('prov_qualified_communication', 'qualifiedCommunicationOf', 'http://www.w3.org/ns/prov#qualifiedCommunicationOf', null, 'recommended'),
    ('prov_qualified_delegation', 'qualifiedDelegationOf', 'http://www.w3.org/ns/prov#qualifiedDelegationOf', null, 'recommended'),
    ('prov_qualified_derivation', 'qualifiedDerivationOf', 'http://www.w3.org/ns/prov#qualifiedDerivationOf', null, 'recommended'),
    ('prov_qualified_end', 'qualifiedEndOf', 'http://www.w3.org/ns/prov#qualifiedEndOf', null, 'recommended'),
    ('prov_qualified_generation', 'qualifiedGenerationOf', 'http://www.w3.org/ns/prov#qualifiedGenerationOf', null, 'recommended'),
    ('prov_qualified_influence', 'qualifiedInfluenceOf', 'http://www.w3.org/ns/prov#qualifiedInfluenceOf', null, 'recommended'),
    ('prov_qualified_invalidation', 'qualifiedInvalidationOf', 'http://www.w3.org/ns/prov#qualifiedInvalidationOf', null, 'recommended'),
    ('prov_qualified_primary_source', 'qualifiedSourceOf', 'http://www.w3.org/ns/prov#qualifiedSourceOf', null, 'recommended'),
    ('prov_qualified_quotation', 'qualifiedQuotationOf', 'http://www.w3.org/ns/prov#qualifiedQuotationOf', null, 'recommended'),
    ('prov_qualified_revision', 'revisedEntity', 'http://www.w3.org/ns/prov#revisedEntity', null, 'recommended'),
    ('prov_qualified_start', 'qualifiedStartOf', 'http://www.w3.org/ns/prov#qualifiedStartOf', null, 'recommended'),
    ('prov_qualified_usage', 'qualifiedUsingActivity', 'http://www.w3.org/ns/prov#qualifiedUsingActivity', null, 'recommended'),
    ('prov_specialization_of', 'generalizationOf', 'http://www.w3.org/ns/prov#generalizationOf', null, 'recommended'),
    ('prov_used', 'wasUsedBy', 'http://www.w3.org/ns/prov#wasUsedBy', null, 'recommended'),
    ('prov_was_associated_with', 'wasAssociateFor', 'http://www.w3.org/ns/prov#wasAssociateFor', null, 'recommended'),
    ('prov_was_attributed_to', 'contributed', 'http://www.w3.org/ns/prov#contributed', null, 'recommended'),
    ('prov_was_derived_from', 'hadDerivation', 'http://www.w3.org/ns/prov#hadDerivation', null, 'recommended'),
    ('prov_was_ended_by', 'ended', 'http://www.w3.org/ns/prov#ended', null, 'recommended'),
    ('prov_was_generated_by', 'generated', 'http://www.w3.org/ns/prov#generated', 'prov_generated', 'defined'),
    ('prov_was_influenced_by', 'influenced', 'http://www.w3.org/ns/prov#influenced', 'prov_influenced', 'defined'),
    ('prov_was_informed_by', 'informed', 'http://www.w3.org/ns/prov#informed', null, 'recommended'),
    ('prov_was_invalidated_by', 'invalidated', 'http://www.w3.org/ns/prov#invalidated', 'prov_invalidated', 'defined'),
    ('prov_was_quoted_from', 'quotedAs', 'http://www.w3.org/ns/prov#quotedAs', null, 'recommended'),
    ('prov_was_revision_of', 'hadRevision', 'http://www.w3.org/ns/prov#hadRevision', null, 'recommended'),
    ('prov_was_started_by', 'started', 'http://www.w3.org/ns/prov#started', null, 'recommended')
on conflict (relation_code) do update set
    inverse_local_name = excluded.inverse_local_name,
    inverse_iri = excluded.inverse_iri,
    inverse_relation_code = excluded.inverse_relation_code,
    inverse_kind_code = excluded.inverse_kind_code;

commit;

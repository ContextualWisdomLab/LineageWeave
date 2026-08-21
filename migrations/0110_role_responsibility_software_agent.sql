-- PROV-O software agents are valid R&R actors (bots, schedulers, and
-- automation), but they do not bind to the person/team/organization catalog.
insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order)
values ('prov_agent_type', 'prov_software_agent', 'Software agent', 3)
on conflict (lookup_code) do nothing;

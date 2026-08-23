begin;

drop view if exists analysis_run_current_status;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'tenant_settings'
          and column_name = 'tenant_settings_id'
    ) then
        alter table public.tenant_settings
            rename column tenant_settings_id to id;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'report_item_parameter'
          and column_name = 'item_slope'
    ) then
        alter table public.report_item_parameter
            rename column item_slope to slope;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'report_item_information'
          and column_name = 'information_value'
    ) then
        alter table public.report_item_information
            rename column information_value to information;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_summary_role'
          and column_name = 'responsibility_text'
    ) then
        alter table public.post_summary_role
            rename column responsibility_text to responsibility;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_project_mention'
          and column_name = 'mention_confidence'
    ) then
        alter table public.post_project_mention
            rename column mention_confidence to confidence;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_content_unit_structure'
          and column_name = 'structure_confidence'
    ) then
        alter table public.post_content_unit_structure
            rename column structure_confidence to confidence;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_content_image_region'
          and column_name = 'image_caption'
    ) then
        alter table public.post_content_image_region
            rename column image_caption to caption;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_content_image'
          and column_name = 'image_caption'
    ) then
        alter table public.post_content_image
            rename column image_caption to caption;
    end if;
end
$$;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'analysis_run_status_event'
          and column_name = 'is_retryable'
    ) then
        alter table public.analysis_run_status_event
            rename column is_retryable to retryable;
    end if;
end
$$;

do $$
begin
    if to_regclass('public.post_bookmark') is not null
       and to_regclass('public.bookmark') is null then
        alter table public.post_bookmark rename to bookmark;
    end if;
end
$$;

alter index if exists public.post_bookmark_post_idx rename to bookmark_post_idx;

do $$
begin
    if to_regclass('public.analysis_run_status_event') is not null then
        execute $view$
            create view analysis_run_current_status as
            select distinct on (status_event.analysis_run_id)
                   status_event.analysis_run_id,
                   status_event.status_code,
                   status_event.status_ordinal,
                   status_event.occurred_at,
                   status_event.recorded_at,
                   status_event.failure_code,
                   status_event.retryable
              from analysis_run_status_event as status_event
             order by status_event.analysis_run_id,
                      status_event.status_ordinal desc
        $view$;
        execute $comment$
            comment on view analysis_run_current_status is
                'Latest append-only status projection for each run; never a second mutable lifecycle authority.'
        $comment$;
    end if;
end
$$;

commit;

-- Validate widened checks without holding the short metadata lock during the scan.
alter table analysis_run validate constraint analysis_run_kind_check;

do $$
begin
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox
            validate constraint analysis_run_outbox_kind_check;
    end if;
end
$$;

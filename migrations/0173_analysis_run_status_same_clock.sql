-- Analysis-run status events share one PostgreSQL write clock (ADR 0167).
--
-- Replaces enforce_analysis_run_status_transition so recorded_at cannot
-- precede occurred_at when a caller supplies a clock that is slightly
-- ahead of PostgreSQL (the live CheckViolationError on
-- analysis_run_status_time_check). Occurrence is not rewritten; the
-- durable write clock is raised to the supplied occurrence when needed.
-- Idempotent migration 0173: create or replace. Does not invent a theta.

create or replace function enforce_analysis_run_status_transition()
returns trigger
language plpgsql
as $$
declare
    previous_ordinal integer;
    previous_status_code text;
    previous_occurred_at timestamptz;
    run_requested_at timestamptz;
    write_clock timestamptz;
begin
    -- The immutable parent row is a per-run serialization lock. It prevents
    -- concurrent writers from both accepting the same next ordinal.
    select requested_at
      into run_requested_at
      from analysis_run
     where analysis_run_id = new.analysis_run_id
     for update;

    if not found then
        raise exception 'analysis_run_not_found';
    end if;
    if not exists (
        select 1 from analysis_run_scope
         where analysis_run_id = new.analysis_run_id
    ) then
        raise exception 'analysis_run_scope_required';
    end if;
    if new.occurred_at < run_requested_at then
        raise exception 'analysis_run_status_before_request';
    end if;
    -- One database clock for the durable write. If the supplied occurrence
    -- is already ahead of that clock (Python datetime.now skew), raise
    -- recorded_at to occurred_at so analysis_run_status_time_check holds
    -- without rewriting occurrence or breaking monotonicity.
    write_clock := clock_timestamp();
    new.recorded_at := write_clock;
    if new.recorded_at < new.occurred_at then
        new.recorded_at := new.occurred_at;
    end if;

    select status_ordinal, status_code, occurred_at
      into previous_ordinal, previous_status_code, previous_occurred_at
      from analysis_run_status_event
     where analysis_run_id = new.analysis_run_id
     order by status_ordinal desc
     limit 1;

    if previous_ordinal is null then
        if new.status_ordinal <> 1
           or new.status_code <> 'analysis_status_pending' then
            raise exception 'analysis_run_first_status_must_be_pending';
        end if;
        return new;
    end if;

    if new.status_ordinal <> previous_ordinal + 1 then
        raise exception 'analysis_run_status_ordinal_not_contiguous';
    end if;
    if new.occurred_at < previous_occurred_at then
        raise exception 'analysis_run_status_time_not_monotonic';
    end if;

    if previous_status_code = 'analysis_status_pending' then
        if new.status_code not in (
            'analysis_status_running',
            'analysis_status_cancelled'
        ) then
            raise exception 'analysis_run_status_transition_invalid';
        end if;
    elsif previous_status_code = 'analysis_status_running' then
        if new.status_code not in (
            'analysis_status_succeeded',
            'analysis_status_failed',
            'analysis_status_cancelled'
        ) then
            raise exception 'analysis_run_status_transition_invalid';
        end if;
    else
        raise exception 'analysis_run_terminal_status_has_no_successor';
    end if;

    return new;
end
$$;

comment on function enforce_analysis_run_status_transition() is
    'Serializes status appends and requires immutable scope, request-time '
    'ordering, database-recorded time that cannot precede occurrence, '
    'legal transitions, and terminal finality.';

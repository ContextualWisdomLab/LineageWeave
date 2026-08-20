-- Analysis-run status write clock (ADR 0013 follow-up / v2.12.6).
--
-- Additive to 0018. Existing status rows stay in place. The 0018 BEFORE
-- INSERT trigger overwrote recorded_at with clock_timestamp() after Python
-- captured occurred_at as datetime.now(timezone.utc). Live PostgreSQL then
-- rejected analysis_run_status_time_check because Python's clock lands
-- ~15-20ms after Postgres clock_timestamp().
--
-- Do not clamp occurred_at down: that would break monotonicity against
-- previously stored Python-ahead occurrence times. Raise recorded_at to
-- the later of database write time and occurrence time. Client-supplied
-- recorded_at remains discarded.

begin;

create or replace function enforce_analysis_run_status_transition()
returns trigger
language plpgsql
as $$
declare
    previous_ordinal integer;
    previous_status_code text;
    previous_occurred_at timestamptz;
    run_requested_at timestamptz;
    database_now timestamptz;
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
    -- Permit bounded client clock skew, but do not accept arbitrary future
    -- events that would manufacture audit time. Do not clamp occurred_at
    -- down: that would break monotonicity against Python-ahead events.
    database_now := clock_timestamp();
    if new.occurred_at > database_now + interval '1 minute' then
        raise exception 'analysis_run_status_time_too_far_in_future';
    end if;
    new.recorded_at := greatest(database_now, new.occurred_at);

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
    'ordering, recorded time at least as late as occurrence, legal transitions, '
    'and terminal finality.';

commit;

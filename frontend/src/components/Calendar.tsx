import type { CalDavEvent } from "../api";

export const CALENDAR_EMPTY = "이 범위의 일정을 아직 받을 수 없습니다";

export type CalendarProps = {
  available: boolean;
  events: CalDavEvent[] | null;
  emptyNextAction?: string | null;
};

export function Calendar({ available, events, emptyNextAction }: CalendarProps) {
  const empty = !available || !events || events.length === 0;
  return (
    <section className="popup-section lineage-home" aria-label="달력">
      <h2>달력</h2>
      {empty ? (
        <p className="popup-placeholder">{emptyNextAction ?? CALENDAR_EMPTY}</p>
      ) : (
        <ul>
          {events.map((event) => (
            <li key={event.event_id}>
              {event.starts_at} · {event.summary}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

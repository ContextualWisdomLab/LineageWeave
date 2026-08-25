import { EvidenceStatusMark } from "./EvidenceStatusMark";
import { CALENDAR_CONSUME_UNAVAILABLE } from "../gnbChrome";
import type { CalendarResponse, NaruonCalendarEvent } from "../api";
import { t } from "../i18n";

export type WorkspaceCalendarProps = {
  calendar: CalendarResponse;
  onSelectPost: (postId: string) => void;
  headingId: string;
  heading: string;
  failClosedCopy?: string;
};

/**
 * Buyer Calendar: observed Naruon occurrences stay separate from
 * post-grounded commitments. Click a commitment to open that post.
 */
export function WorkspaceCalendar({
  calendar,
  onSelectPost,
  headingId,
  heading,
  failClosedCopy = CALENDAR_CONSUME_UNAVAILABLE,
}: WorkspaceCalendarProps) {
  const events = calendar.events ?? [];
  const commitments = calendar.commitments ?? [];
  const naruonAvailable = calendar.calendar_sources?.naruon_available ?? false;
  const naruonNextAction = calendar.calendar_sources?.naruon_next_action;

  return (
    <section className="popup-section lineage-home" aria-labelledby={headingId}>
      <h2 id={headingId}>{heading}</h2>
      <section className="popup-section" aria-labelledby={`${headingId}-observed`}>
        <h3 id={`${headingId}-observed`}>{t("Observed calendar events")}</h3>
        {events.length === 0 ? (
          <p className="popup-placeholder" role="status">
            {naruonAvailable
              ? t("No observed calendar events are available.")
              : failClosedCopy}
          </p>
        ) : (
          <ul className="ticket-list" aria-label={t("Observed calendar events")}>
            {events.map((event) => (
              <ObservedEventRow key={event.occurrence_reference} event={event} />
            ))}
          </ul>
        )}
        {!naruonAvailable && naruonNextAction ? (
          <p className="popup-placeholder">{naruonNextAction}</p>
        ) : null}
      </section>
      <section className="popup-section" aria-labelledby={`${headingId}-commitments`}>
        <h3 id={`${headingId}-commitments`}>{t("Upcoming commitments")}</h3>
        {commitments.length === 0 ? (
          <p className="popup-placeholder">
            {t("No upcoming commitments. Derive one from a post, or create a ticket with a due date.")}
          </p>
        ) : (
          <ul className="ticket-list">
            {commitments.map((entry) => (
              <li key={entry.issue_ticket_id} className="ticket-list-item">
                <button
                  type="button"
                  className="post-list-item"
                  aria-label={`${t("Open commitment for:")} ${entry.post_title}`}
                  onClick={() => onSelectPost(entry.post_id)}
                >
                  <span className="ticket-title">
                    {entry.commitment_summary ?? entry.ticket_title}
                  </span>
                  <span className="post-badge">{entry.post_title}</span>
                  <span className="post-badge">
                    {entry.ticket_status_label ?? entry.ticket_status_code}
                  </span>
                  <span className="post-badge">
                    {t("due")} {entry.due_date}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function ObservedEventRow({ event }: { event: NaruonCalendarEvent }) {
  return (
    <li className="ticket-list-item">
      <div className="post-list-item">
        <EvidenceStatusMark status="evidence" />
        <span className="ticket-title">{event.display_text}</span>
        <span className="post-badge">{event.starts_at}</span>
        <span className="post-badge">{event.disclosure_code}</span>
        <span className="post-badge">
          {t("Open this observed occurrence. It is not a LineageWeave commitment.")}
        </span>
      </div>
    </li>
  );
}

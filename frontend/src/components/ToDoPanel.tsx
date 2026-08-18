import type { IssueTicket } from "../api";

export const TODO_EMPTY = "이 사건의 할 일이 아직 없습니다";

export type ToDoPanelProps = {
  tickets: IssueTicket[] | null;
  error?: string | null;
};

export function ToDoPanel({ tickets, error }: ToDoPanelProps) {
  return (
    <section className="popup-section" aria-label="할 일">
      <h3>할 일</h3>
      {error ? <p className="error">{error}</p> : null}
      {tickets === null && !error ? <p>Loading to-dos...</p> : null}
      {tickets && tickets.length === 0 ? <p className="popup-placeholder">{TODO_EMPTY}</p> : null}
      {tickets && tickets.length > 0 ? (
        <ul>
          {tickets.map((ticket) => (
            <li key={ticket.issue_ticket_id}>
              {ticket.ticket_status_label ?? ticket.ticket_status_code}
              {" · "}
              {ticket.commitment_summary ?? ticket.ticket_title}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

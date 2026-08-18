import type { IssueTicket } from "../api";

export const COMMITMENTS_EMPTY = "이 사건의 고객 약속이 아직 없습니다";

export type CommitmentsPanelProps = {
  tickets: IssueTicket[] | null;
  error?: string | null;
};

export function CommitmentsPanel({ tickets, error }: CommitmentsPanelProps) {
  const commitments = tickets?.filter((ticket) => ticket.commitment_summary || ticket.due_date) ?? null;
  return (
    <section className="popup-section" aria-label="고객 약속">
      <h3>고객 약속</h3>
      {error ? <p className="error">{error}</p> : null}
      {tickets === null && !error ? <p>Loading commitments...</p> : null}
      {commitments && commitments.length === 0 ? (
        <p className="popup-placeholder">{COMMITMENTS_EMPTY}</p>
      ) : null}
      {commitments && commitments.length > 0 ? (
        <ul>
          {commitments.map((ticket) => (
            <li key={ticket.issue_ticket_id}>
              {ticket.commitment_summary ?? ticket.ticket_title}
              {ticket.due_date ? ` · ${ticket.due_date}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

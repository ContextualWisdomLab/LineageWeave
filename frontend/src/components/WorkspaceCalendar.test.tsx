import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceCalendar } from "./WorkspaceCalendar";
import { CALENDAR_CONSUME_UNAVAILABLE } from "../gnbChrome";
import type { CalendarResponse } from "../api";

const commitment = {
  issue_ticket_id: "ticket-a100",
  post_id: "post-demo-public",
  ticket_status_code: "open",
  ticket_status_label: "Open",
  ticket_title: "Send Northridge Grid the revised quote",
  assigned_account_id: null,
  due_date: "2026-01-12",
  commitment_summary: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  post_title: "Public post",
};

const unavailable: CalendarResponse = {
  events: [],
  commitments: [commitment],
  calendar_sources: {
    naruon_available: false,
    naruon_next_action:
      "Ask your workspace administrator to enable calendar access. Open a commitment below to read its source post.",
  },
};

describe("WorkspaceCalendar", () => {
  it("fails closed on observed events and still opens a commitment", async () => {
    const onSelectPost = vi.fn();
    render(
      <WorkspaceCalendar
        calendar={unavailable}
        onSelectPost={onSelectPost}
        headingId="calendar-heading"
        heading="달력"
      />,
    );

    expect(screen.getByRole("heading", { name: "달력" })).toBeInTheDocument();
    expect(screen.getByText(CALENDAR_CONSUME_UNAVAILABLE)).toBeInTheDocument();
    const notice = screen.getByRole("region", { name: /^Unavailable:/ });
    expect(notice).toHaveTextContent(CALENDAR_CONSUME_UNAVAILABLE);
    expect(notice).toHaveTextContent("enable calendar access");
    expect(notice).not.toHaveTextContent(/Naruon|provider|model|transport|environment/i);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByText(/CalDAV/i)).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /open commitment for: public post/i }),
    );
    expect(onSelectPost).toHaveBeenCalledWith("post-demo-public");
  });

  it("does not turn an observed occurrence into a commitment button", () => {
    render(
      <WorkspaceCalendar
        calendar={{
          ...unavailable,
          events: [
            {
              occurrence_reference: "occ_001",
              event_reference: "evt_001",
              source_reference: "src_001",
              display_text: "Customer review",
              starts_at: "2026-08-24T09:00:00+09:00",
              ends_at: "2026-08-24T10:00:00+09:00",
              all_day: false,
              time_zone: "Asia/Seoul",
              status_code: "confirmed",
              disclosure_code: "summary_visible",
              truth_status_code: "observed",
              observed_at: "2026-08-21T00:00:00Z",
              provider_revision: 'W/"revision-7"',
            },
          ],
          calendar_sources: { naruon_available: true, naruon_next_action: null },
        }}
        onSelectPost={() => undefined}
        headingId="calendar-heading"
        heading="달력"
      />,
    );

    expect(screen.getByText("Customer review")).toBeInTheDocument();
    expect(
      screen.getByText("Open this observed occurrence. It is not a LineageWeave commitment."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /customer review/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open commitment for: public post/i })).toBeInTheDocument();
  });
});

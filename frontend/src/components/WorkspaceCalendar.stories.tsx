import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { WorkspaceCalendar } from "./WorkspaceCalendar";
import type { CalendarResponse } from "../api";
import "../App.css";

const unavailable: CalendarResponse = {
  events: [],
  commitments: [
    {
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
    },
  ],
  calendar_sources: {
    naruon_available: false,
    naruon_next_action:
      "Connect the Naruon calendar projection. Open a commitment below to read that post.",
  },
};

const observed: CalendarResponse = {
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
  commitments: unavailable.commitments,
  calendar_sources: { naruon_available: true, naruon_next_action: null },
};

const meta = {
  title: "Workspace/WorkspaceCalendar",
  component: WorkspaceCalendar,
  args: {
    calendar: unavailable,
    onSelectPost: () => undefined,
    headingId: "calendar-heading",
    heading: "달력",
  },
} satisfies Meta<typeof WorkspaceCalendar>;

export default meta;

type Story = StoryObj<typeof meta>;

export const NaruonUnavailable: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const notice = canvas.getByRole("region", { name: /^Unavailable:/ });
    await expect(notice).toHaveTextContent("이 범위의 일정을 아직 받을 수 없습니다");
    await expect(notice).toHaveTextContent("Connect the Naruon calendar projection");
    await expect(
      canvas.getByRole("button", { name: /open commitment for: public post/i }),
    ).toBeVisible();
  },
};

export const ObservedOccurrence: Story = {
  args: { calendar: observed },
};

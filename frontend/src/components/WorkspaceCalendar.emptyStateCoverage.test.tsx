import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CalendarResponse } from "../api";
import { setLocale } from "../i18n";
import { WorkspaceCalendar } from "./WorkspaceCalendar";

const availableButEmpty: CalendarResponse = {
  events: [],
  commitments: [],
  calendar_sources: {
    naruon_available: true,
    naruon_next_action: null,
  },
};

const unavailableWithoutNextAction: CalendarResponse = {
  events: [],
  commitments: [],
  calendar_sources: {
    naruon_available: false,
    naruon_next_action: null,
  },
};

describe("WorkspaceCalendar optional states", () => {
  beforeEach(() => {
    setLocale("en");
  });

  it("keeps observed-event and commitment emptiness distinct when the calendar source is available", () => {
    const onSelectPost = vi.fn();

    render(
      <WorkspaceCalendar
        calendar={availableButEmpty}
        onSelectPost={onSelectPost}
        headingId="calendar-empty-heading"
        heading="Calendar"
      />,
    );

    expect(screen.getByText("No observed calendar events are available.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No upcoming commitments. Derive one from a post, or create a ticket with a due date.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /^Unavailable:/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open commitment for:/i })).not.toBeInTheDocument();
    expect(onSelectPost).not.toHaveBeenCalled();
  });

  it("does not invent a provider next action when the unavailable source supplies none", () => {
    render(
      <WorkspaceCalendar
        calendar={unavailableWithoutNextAction}
        onSelectPost={() => undefined}
        headingId="calendar-unavailable-heading"
        heading="Calendar"
      />,
    );

    const notice = screen.getByRole("region", { name: /^Unavailable:/ });
    expect(notice).toBeInTheDocument();
    expect(notice.querySelector(".status-notice-next-action")).toBeNull();
    expect(screen.queryByText("No observed calendar events are available.")).not.toBeInTheDocument();
  });
});

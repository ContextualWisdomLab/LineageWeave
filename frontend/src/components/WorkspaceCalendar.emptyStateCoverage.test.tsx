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

describe("WorkspaceCalendar available empty states", () => {
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
});

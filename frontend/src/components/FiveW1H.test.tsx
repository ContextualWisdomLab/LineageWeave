import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FiveW1H } from "./FiveW1H";

describe("FiveW1H", () => {
  it("shows buyer guidance for an empty dimension without leaking the action code", () => {
    render(
      <FiveW1H
        slots={[
          {
            slot_code: "when",
            values: [],
            empty_next_action_code: "inspect_source_body_or_related_posts",
          },
          {
            slot_code: "why",
            values: [],
            empty_next_action_code: "future_action_code",
          },
        ]}
      />,
    );

    expect(screen.getAllByText("No grounded evidence for this dimension.")).toHaveLength(2);
    expect(
      screen.getByText("Review the source body or related posts for this dimension."),
    ).toBeInTheDocument();
    expect(screen.getByText("Review source evidence for this dimension.")).toBeInTheDocument();
    expect(screen.queryByText("inspect_source_body_or_related_posts")).not.toBeInTheDocument();
    expect(screen.queryByText("future_action_code")).not.toBeInTheDocument();
  });
});

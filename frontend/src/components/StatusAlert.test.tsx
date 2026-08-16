import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusAlert } from "./StatusAlert";

describe("StatusAlert", () => {
  it("announces the next action as an alert", () => {
    render(
      <StatusAlert>
        This run is not on your list. Open a visible run from the home list, or request a lineage reconstruction for a corporation you already walk.
      </StatusAlert>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "This run is not on your list. Open a visible run from the home list, or request a lineage reconstruction for a corporation you already walk.",
    );
    expect(screen.queryByText(/thread-group/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/knowledge_cutoff/i)).not.toBeInTheDocument();
  });
});

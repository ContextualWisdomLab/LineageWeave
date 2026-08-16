import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBadge } from "./PostBadge";

describe("PostBadge", () => {
  it("tells the operator the live title was rewritten after the run", () => {
    render(<PostBadge>Updated after cutoff</PostBadge>);
    expect(screen.getByText("Updated after cutoff")).toBeInTheDocument();
  });
});

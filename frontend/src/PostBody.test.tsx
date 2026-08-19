import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

describe("PostBody", () => {
  it("keeps raw indentation when persisted structure is unresolved", () => {
    render(
      <PostBody
        body="<p>&nbsp;&nbsp;Nested item</p><p>Root item</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_text: "Nested item",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
          {
            unit_index: 1,
            unit_kind_code: "dom",
            unit_text: "Root item",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    expect(screen.getByText("Nested item")).toHaveAttribute("data-indent-level", "1");
    expect(screen.getByText("Root item")).toHaveAttribute("data-indent-level", "0");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

describe("PostBody table-source indentation matching", () => {
  it("does not reuse an earlier table cell when a later paragraph has the same text", () => {
    render(
      <PostBody
        body="<table><tr><td>Repeated</td></tr></table><p>&nbsp;&nbsp;Repeated</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_label: "tr",
            unit_text: "Repeated",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "table row",
          },
          {
            unit_index: 1,
            unit_kind_code: "dom",
            unit_text: "Repeated",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    const repeatedNodes = screen.getAllByText("Repeated");
    const paragraph = repeatedNodes.find((node) => node.tagName === "P");

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(paragraph).toBeDefined();
    expect(paragraph).toHaveAttribute("data-indent-level", "1");
  });
});

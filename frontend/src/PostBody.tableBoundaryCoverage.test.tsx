import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

const persistedRow = (unit_index: number, left: string, right: string) => ({
  unit_index,
  unit_kind_code: "dom",
  unit_label: "tr",
  unit_text: `${left} | ${right}`,
  indent_level: 0,
  indent_source_code: "explicit" as const,
  indent_confidence: 1,
  indent_evidence: "Synthetic persisted table row",
});

describe("PostBody persisted table boundaries", () => {
  it("falls back to one persisted row group when source table row counts are stale", () => {
    render(
      <PostBody
        body={
          "<table><tr><td>Source A</td><td>Source B</td></tr></table>" +
          "<table><tr><td>Stale A</td><td>Stale B</td></tr><tr><td>Stale C</td><td>Stale D</td></tr></table>"
        }
        structureUnits={[
          persistedRow(0, "Persisted A", "Persisted B"),
          persistedRow(1, "Persisted C", "Persisted D"),
        ]}
      />,
    );

    const tables = screen.getAllByRole("table");
    expect(tables).toHaveLength(1);
    expect(within(tables[0]).getAllByRole("row")).toHaveLength(2);
    expect(within(tables[0]).getByText("Persisted A")).toBeInTheDocument();
    expect(within(tables[0]).getByText("Persisted D")).toBeInTheDocument();
  });

  it("counts only direct and row-group table rows when source tables contain metadata children", () => {
    render(
      <PostBody
        body={
          "<table><caption>First table</caption><colgroup><col /></colgroup><tr><td>A</td><td>B</td></tr></table>" +
          "<table><caption>Second table</caption><tbody><tr><td>C</td><td>D</td></tr><tr><td>E</td><td>F</td></tr></tbody></table>"
        }
        structureUnits={[
          persistedRow(0, "A", "B"),
          persistedRow(1, "C", "D"),
          persistedRow(2, "E", "F"),
        ]}
      />,
    );

    const tables = screen.getAllByRole("table");
    expect(tables).toHaveLength(2);
    expect(within(tables[0]).getAllByRole("row")).toHaveLength(1);
    expect(within(tables[1]).getAllByRole("row")).toHaveLength(2);
  });
});

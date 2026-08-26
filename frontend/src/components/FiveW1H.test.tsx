import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FiveW1H } from "./FiveW1H";
import type { FiveW1HSlot } from "../api";

function slot(overrides: Partial<FiveW1HSlot>): FiveW1HSlot {
  return {
    slot_code: "who",
    values: [],
    empty_next_action_code: "none",
    ...overrides,
  };
}

describe("FiveW1H", () => {
  it("shows a loading state while slots have not arrived yet", () => {
    render(<FiveW1H slots={null} />);
    expect(screen.getByText("Loading 5W1H...")).toBeInTheDocument();
  });

  it("shows a no-evidence message for a slot with no values", () => {
    render(<FiveW1H slots={[slot({ slot_code: "why", values: [] })]} />);
    expect(screen.getByText("No grounded evidence for this dimension.")).toBeInTheDocument();
  });

  it("renders a human label for a raw evidence source instead of the dotted path", () => {
    render(
      <FiveW1H
        slots={[
          slot({
            slot_code: "who",
            values: [
              {
                text: "Ada West",
                source: "post_summary_role.affiliated_organization_name",
                ontology_codes: [],
                ontology_annotations: {},
              },
            ],
          }),
        ]}
      />,
    );
    expect(screen.getByText("Ada West")).toBeInTheDocument();
    expect(screen.getByText("Extracted affiliation")).toBeInTheDocument();
    expect(screen.queryByText("post_summary_role.affiliated_organization_name")).not.toBeInTheDocument();
  });

  it("falls back to the raw source string for an unmapped evidence source", () => {
    render(
      <FiveW1H
        slots={[
          slot({
            slot_code: "how",
            values: [
              {
                text: "Filed via portal",
                source: "some_future_source",
                ontology_codes: [],
                ontology_annotations: {},
              },
            ],
          }),
        ]}
      />,
    );
    expect(screen.getByText("some_future_source")).toBeInTheDocument();
  });

  it("shows optional evidence text and ontology class badges only when present", async () => {
    render(
      <FiveW1H
        slots={[
          slot({
            slot_code: "what",
            values: [
              {
                text: "Renewed the vendor contract",
                source: "post_summary_event",
                evidence_text: "“we renewed the contract”",
                ontology_codes: ["evt-42"],
                ontology_annotations: { ontology_label: "Contract renewal" },
              },
            ],
          }),
        ]}
      />,
    );

    await userEvent.click(screen.getByText("Supporting details"));
    expect(screen.getByText("“we renewed the contract”")).toBeInTheDocument();
    expect(screen.getByText("Contract renewal")).toBeInTheDocument();
  });

  it("falls back to the ontology code when no ontology label is annotated", async () => {
    render(
      <FiveW1H
        slots={[
          slot({
            slot_code: "what",
            values: [
              {
                text: "Renewed the vendor contract",
                source: "post_summary_event",
                ontology_codes: ["evt-42"],
                ontology_annotations: {},
              },
            ],
          }),
        ]}
      />,
    );

    await userEvent.click(screen.getByText("Supporting details"));
    expect(screen.getByText("Related detail")).toBeInTheDocument();
  });

  it("renders one definition entry per slot with its human label", () => {
    render(
      <FiveW1H
        slots={[
          slot({ slot_code: "who", values: [] }),
          slot({ slot_code: "when", values: [] }),
          slot({ slot_code: "where", values: [] }),
        ]}
      />,
    );
    expect(screen.getByText("Who")).toBeInTheDocument();
    expect(screen.getByText("When")).toBeInTheDocument();
    expect(screen.getByText("Where")).toBeInTheDocument();
  });

  it("renders multiple values for the same slot as separate list items", () => {
    render(
      <FiveW1H
        slots={[
          slot({
            slot_code: "who",
            values: [
              { text: "Ada West", source: "post_summary_role", ontology_codes: [], ontology_annotations: {} },
              { text: "Priya Nair", source: "post_summary_role", ontology_codes: [], ontology_annotations: {} },
            ],
          }),
        ]}
      />,
    );
    expect(screen.getByText("Ada West")).toBeInTheDocument();
    expect(screen.getByText("Priya Nair")).toBeInTheDocument();
  });

  it("exposes the section under an accessible landmark name", () => {
    render(<FiveW1H slots={null} />);
    expect(screen.getByRole("region", { name: "5W1H" })).toBeInTheDocument();
  });
});

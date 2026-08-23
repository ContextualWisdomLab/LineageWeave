import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FiveW1H } from "./FiveW1H";

describe("FiveW1H", () => {
  it("shows an honest loading state", () => {
    render(<FiveW1H slots={null} />);

    expect(screen.getByText("Loading 5W1H...")).toBeInTheDocument();
  });

  it("renders values with reader-facing evidence and ontology provenance", () => {
    render(
      <FiveW1H
        slots={[
          {
            slot_code: "who",
            empty_next_action_code: "",
            values: [
              {
                text: "Synthetic account team",
                source: "post_summary_role",
                evidence_text: "Named in the synthetic source.",
                ontology_codes: ["prov:Agent"],
                ontology_annotations: { ontology_label: "Agent" },
              },
              {
                text: "Synthetic reviewer",
                source: "custom_source",
                evidence_text: "",
                ontology_codes: ["ex:Reviewer"],
                ontology_annotations: {},
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("Synthetic account team")).toBeInTheDocument();
    expect(screen.getByText("Extracted role")).toBeInTheDocument();
    expect(screen.getByText("Named in the synthetic source.")).toBeInTheDocument();
    expect(screen.getByText("Ontology class: Agent")).toBeInTheDocument();
    expect(screen.getByText("custom_source")).toBeInTheDocument();
    expect(screen.getByText("Ontology class: ex:Reviewer")).toBeInTheDocument();
  });

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

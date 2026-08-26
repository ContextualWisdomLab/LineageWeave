import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VoicePerspectiveList } from "../App";

describe("VoicePerspectiveList", () => {
  it("keeps primary and evidence-connected perspectives distinct", () => {
    render(
      <VoicePerspectiveList
        voices={[
          {
            code: "voc",
            label: "Voice of Customer",
            is_primary: true,
            truth_status_code: "truth_observed",
            evidence_available: false,
          },
          {
            code: "vops",
            label: "Voice of Process",
            is_primary: false,
            truth_status_code: "truth_observed",
            evidence_available: true,
          },
          {
            code: "vreg",
            label: "Voice of Regulator",
            is_primary: false,
            truth_status_code: "truth_rejected",
            evidence_available: true,
          },
        ]}
      />,
    );

    const perspectives = screen.getByRole("region", { name: "Recorded perspectives" });
    expect(within(perspectives).getByText("Voice of Customer (Observed)")).toBeInTheDocument();
    expect(within(perspectives).getByText("Voice of Process (Observed)")).toBeInTheDocument();
    expect(within(perspectives).getByText("Voice of Regulator (Rejected)")).toBeInTheDocument();
    expect(within(perspectives).getByText("Imported from source")).toBeInTheDocument();
    expect(within(perspectives).getAllByText("Evidence connected")).toHaveLength(2);
  });
});

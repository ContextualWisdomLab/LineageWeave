import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
            code: "vor",
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

  it("offers the authorized evidence view only for an additional perspective", async () => {
    const onViewEvidence = vi.fn();
    const primary = {
      code: "voc",
      label: "Voice of Customer",
      is_primary: true,
      truth_status_code: "truth_observed",
      evidence_available: false,
    };
    const { rerender } = render(
      <VoicePerspectiveList voices={[primary]} onViewEvidence={onViewEvidence} />,
    );
    expect(screen.queryByRole("button", { name: "View evidence" })).not.toBeInTheDocument();

    rerender(
      <VoicePerspectiveList
        voices={[primary, { ...primary, code: "vops", is_primary: false, evidence_available: true }]}
        onViewEvidence={onViewEvidence}
        evidenceOpen={false}
      />,
    );
    const button = screen.getByRole("button", { name: "View evidence" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(button);
    expect(onViewEvidence).toHaveBeenCalledOnce();
  });

  it("keeps an additional perspective visible without claiming absent derivation evidence", () => {
    const onViewEvidence = vi.fn();
    const unavailable = {
      code: "vops",
      label: "Voice of Process",
      is_primary: false,
      truth_status_code: "truth_proposed",
      evidence_available: false,
    };
    const primary = { ...unavailable, code: "voc", label: "Voice of Customer", is_primary: true };
    const { rerender } = render(
      <VoicePerspectiveList voices={[primary, unavailable]} onViewEvidence={onViewEvidence} />,
    );
    const perspectives = screen.getByRole("region", { name: "Recorded perspectives" });
    expect(within(perspectives).getByText("Voice of Process (Proposed)")).toBeInTheDocument();
    expect(within(perspectives).getByText("Evidence unavailable. Ask an administrator to check this perspective.")).toBeInTheDocument();
    expect(within(perspectives).queryByRole("button", { name: "View evidence" })).not.toBeInTheDocument();

    rerender(
      <VoicePerspectiveList
        voices={[primary, unavailable, { ...unavailable, code: "vor", label: "Voice of Regulator", evidence_available: true }]}
        onViewEvidence={onViewEvidence}
      />,
    );
    expect(within(perspectives).getByText("Evidence unavailable. Ask an administrator to check this perspective.")).toBeInTheDocument();
    expect(within(perspectives).getByText("Evidence connected")).toBeInTheDocument();
    expect(within(perspectives).getByRole("button", { name: "View evidence" })).toBeInTheDocument();
  });
});

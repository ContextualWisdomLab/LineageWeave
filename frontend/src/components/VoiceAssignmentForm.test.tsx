import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VoiceAssignmentForm } from "../App";
import { canAuthorVoice, postPrimaryVoiceLabel } from "../voicePerspective";

describe("VoiceAssignmentForm", () => {
  it("does not substitute the live primary Voice into a cutoff with no assignment", () => {
    const post = {
      voc_type_code: "voc",
      voc_type_label: "Voice of Customer",
      voice_types: [],
    };

    expect(postPrimaryVoiceLabel(post, "2026-01-01T00:00:00Z")).toBe(
      "Perspective unavailable at this cutoff",
    );
    expect(postPrimaryVoiceLabel(post)).toBe("Voice of Customer");
    expect(canAuthorVoice(true, "2026-01-01T00:00:00Z")).toBe(false);
    expect(canAuthorVoice(false)).toBe(false);
    expect(canAuthorVoice(true)).toBe(true);
  });

  it("requires an explicit unassigned perspective and evidence status", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <VoiceAssignmentForm
        voices={[
          {
            code: "voc",
            label: "Voice of Customer",
            is_primary: true,
            truth_status_code: "truth_observed",
            evidence_available: true,
          },
        ]}
        options={[
          { code: "voc", label: "Voice of Customer" },
          { code: "vops", label: "Voice of Process" },
        ]}
        onSave={onSave}
      />,
    );

    expect(screen.queryByRole("option", { name: "Voice of Customer" })).toBeNull();
    const submit = screen.getByRole("button", { name: "Connect perspective" });
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Perspective"), { target: { value: "vops" } });
    fireEvent.change(screen.getByLabelText("Evidence status"), {
      target: { value: "truth_observed" },
    });
    fireEvent.click(submit);

    expect(await screen.findByRole("status")).toHaveTextContent("Perspective connected.");
    expect(onSave).toHaveBeenCalledWith("vops", "truth_observed");
  });

  it("keeps the submitted values available after a failed save", async () => {
    render(
      <VoiceAssignmentForm
        voices={[]}
        options={[{ code: "vreg", label: "Voice of Regulator" }]}
        onSave={vi.fn().mockRejectedValue(new Error("Evidence is no longer visible."))}
      />,
    );

    fireEvent.change(screen.getByLabelText("Perspective"), { target: { value: "vreg" } });
    fireEvent.change(screen.getByLabelText("Evidence status"), {
      target: { value: "truth_proposed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect perspective" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Evidence is no longer visible.");
    expect(screen.getByLabelText("Perspective")).toHaveValue("vreg");
    expect(screen.getByLabelText("Evidence status")).toHaveValue("truth_proposed");
  });
});

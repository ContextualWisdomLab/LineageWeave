import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VoiceAssignmentForm } from "../App";
import { BackendError } from "../api";
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

    expect(await screen.findByRole("region", { name: /Ready:/ })).toHaveTextContent("Perspective connected.");
    expect(onSave).toHaveBeenCalledWith("vops", "truth_observed");
  });

  it("keeps the submitted values available after a failed save", async () => {
    render(
      <VoiceAssignmentForm
        voices={[]}
        options={[{ code: "vor", label: "Voice of Regulator" }]}
        onSave={vi.fn().mockRejectedValue(new Error("private provider response sentinel"))}
      />,
    );

    fireEvent.change(screen.getByLabelText("Perspective"), { target: { value: "vor" } });
    fireEvent.change(screen.getByLabelText("Evidence status"), {
      target: { value: "truth_proposed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect perspective" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Perspective could not be connected.");
    expect(screen.getByRole("alert")).toHaveTextContent("Review your selections and choose Connect perspective to try again.");
    expect(screen.queryByText(/private provider response sentinel/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Perspective")).toHaveValue("vor");
    expect(screen.getByLabelText("Evidence status")).toHaveValue("truth_proposed");
  });

  it.each([401, 403, 404, 409])("does not offer the same save after HTTP %s", async (status) => {
    const onSave = vi.fn().mockRejectedValue(new BackendError("/private-synthetic-path", status, "private detail sentinel"));
    render(<VoiceAssignmentForm voices={[]} options={[{ code: "vor", label: "Voice of Regulator" }]} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText("Perspective"), { target: { value: "vor" } });
    fireEvent.change(screen.getByLabelText("Evidence status"), { target: { value: "truth_proposed" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect perspective" }));

    const notice = await screen.findByRole("region", { name: /Unavailable:/ });
    expect(notice).toHaveTextContent(status === 401
      ? "Sign in again, then reopen this post."
      : "Reopen this post to check your access and its recorded perspectives.");
    expect(screen.queryByText(/private detail sentinel|private-synthetic-path/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect perspective" })).toBeDisabled();
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("retries the retained selection once and reports success only after saving", async () => {
    let finish!: () => void;
    const onSave = vi.fn().mockRejectedValueOnce(new Error("private detail sentinel"))
      .mockImplementationOnce(() => new Promise<void>((resolve) => { finish = resolve; }));
    render(<VoiceAssignmentForm voices={[]} options={[{ code: "vops", label: "Voice of Process" }]} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText("Perspective"), { target: { value: "vops" } });
    fireEvent.change(screen.getByLabelText("Evidence status"), { target: { value: "truth_observed" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect perspective" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Connect perspective" }));
    expect(screen.getByRole("button", { name: "Connecting..." })).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText("Perspective connected.")).not.toBeInTheDocument();
    finish();
    expect(await screen.findByRole("region", { name: /Ready:/ })).toHaveTextContent("Perspective connected.");
    expect(onSave.mock.calls).toEqual([["vops", "truth_observed"], ["vops", "truth_observed"]]);
  });
});

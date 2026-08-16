import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ANALYSIS_RUN_DIGEST_TARGET_MIN_PX } from "./analysisRunDigests";
import { AnalysisRunReproducibilityDigests } from "./AnalysisRunReproducibilityDigests";

const CODE_REVISION_SHA = "abcdef0123456789deadbeefcafebabe";
const CONFIGURATION_SHA256 =
  "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

describe("AnalysisRunReproducibilityDigests", () => {
  it("renders nothing when the run has no digests", () => {
    const { container } = render(<AnalysisRunReproducibilityDigests />);
    expect(container).toBeEmptyDOMElement();
  });

  it("keeps prefixes audible and hides full digests until activation", () => {
    render(
      <AnalysisRunReproducibilityDigests
        codeRevisionSha={CODE_REVISION_SHA}
        configurationSha256={CONFIGURATION_SHA256}
      />,
    );
    const group = screen.getByLabelText("Analysis run reproducibility digests");
    expect(group).toHaveTextContent("Activate a prefix to read the full digest and match the API payload.");
    expect(group).not.toHaveTextContent("Hover");
    const codeButton = screen.getByRole("button", { name: "Code abcdef012345" });
    const configButton = screen.getByRole("button", { name: "Config 0123456789ab" });
    expect(codeButton).toHaveAttribute("aria-expanded", "false");
    expect(configButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText(CODE_REVISION_SHA)).not.toBeVisible();
    expect(screen.getByText(CONFIGURATION_SHA256)).not.toBeVisible();
    const codePanelId = codeButton.getAttribute("aria-controls");
    const configPanelId = configButton.getAttribute("aria-controls");
    expect(codePanelId).toBeTruthy();
    expect(configPanelId).toBeTruthy();
    expect(document.getElementById(codePanelId ?? "")).toHaveAttribute("hidden");
    expect(document.getElementById(configPanelId ?? "")).toHaveAttribute("hidden");
    expect(codeButton).toHaveStyle({
      minHeight: `${ANALYSIS_RUN_DIGEST_TARGET_MIN_PX}px`,
      minWidth: `${ANALYSIS_RUN_DIGEST_TARGET_MIN_PX}px`,
    });
    expect(configButton).toHaveStyle({
      minHeight: `${ANALYSIS_RUN_DIGEST_TARGET_MIN_PX}px`,
      minWidth: `${ANALYSIS_RUN_DIGEST_TARGET_MIN_PX}px`,
    });
  });

  it("reveals the full code digest with Enter and hides it on the next activation", async () => {
    const user = userEvent.setup();
    render(
      <AnalysisRunReproducibilityDigests
        codeRevisionSha={CODE_REVISION_SHA}
        configurationSha256={CONFIGURATION_SHA256}
      />,
    );
    await user.tab();
    expect(screen.getByRole("button", { name: "Code abcdef012345" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Code abcdef012345" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText(CODE_REVISION_SHA)).toBeVisible();
    expect(screen.getByText(CONFIGURATION_SHA256)).not.toBeVisible();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Code abcdef012345" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.getByText(CODE_REVISION_SHA)).not.toBeVisible();
  });

  it("tells the operator to match the revealed digest after activation", async () => {
    const user = userEvent.setup();
    render(
      <AnalysisRunReproducibilityDigests
        codeRevisionSha={CODE_REVISION_SHA}
        configurationSha256={CONFIGURATION_SHA256}
      />,
    );
    expect(
      screen.getByText("Activate a prefix to read the full digest and match the API payload."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Code abcdef012345" }));
    expect(
      screen.getByText("Match the revealed digest to the API payload."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Activate a prefix to read the full digest and match the API payload."),
    ).not.toBeInTheDocument();
  });

  it("reveals the full configuration digest with Space", async () => {
    const user = userEvent.setup();
    render(
      <AnalysisRunReproducibilityDigests
        codeRevisionSha={CODE_REVISION_SHA}
        configurationSha256={CONFIGURATION_SHA256}
      />,
    );
    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "Config 0123456789ab" })).toHaveFocus();
    await user.keyboard(" ");
    const configButton = screen.getByRole("button", { name: "Config 0123456789ab" });
    expect(configButton).toHaveAttribute("aria-expanded", "true");
    const configPanelId = configButton.getAttribute("aria-controls");
    expect(configPanelId).toBeTruthy();
    expect(document.getElementById(configPanelId ?? "")).not.toHaveAttribute("hidden");
    expect(screen.getByText(CONFIGURATION_SHA256)).toBeVisible();
    expect(screen.getByText(CODE_REVISION_SHA)).not.toBeVisible();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
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
    expect(group).not.toHaveTextContent(CODE_REVISION_SHA);
    expect(group).not.toHaveTextContent(CONFIGURATION_SHA256);
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
    expect(screen.getByText(CODE_REVISION_SHA)).toBeInTheDocument();
    expect(screen.queryByText(CONFIGURATION_SHA256)).not.toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Code abcdef012345" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.queryByText(CODE_REVISION_SHA)).not.toBeInTheDocument();
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
    expect(screen.getByText(CONFIGURATION_SHA256)).toBeInTheDocument();
    expect(screen.queryByText(CODE_REVISION_SHA)).not.toBeInTheDocument();
  });
});

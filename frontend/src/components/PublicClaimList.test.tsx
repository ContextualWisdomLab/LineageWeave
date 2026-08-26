import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PublicClaimVerdict } from "../api";
import { PublicClaimList } from "./PublicClaimList";

const SUPPORTED: PublicClaimVerdict = {
  public_claim_envelope_id: "env-demo-public",
  source_post_id: "post-demo-public",
  source_post_title: "Public post",
  claim_kind_code: "claim_organization_presence",
  subject_label: "Northridge Grid",
  claim_text: "Northridge Grid is a power utility named on the Demo public post.",
  status_code: "claim_supported",
  external_evidence_urls: ["https://northridgegrid.example/about"],
  next_action: "Public web evidence supports this claim. Open that post.",
};

describe("PublicClaimList", () => {
  it("names the public claim so the next click opens that post", async () => {
    const onSelectPost = vi.fn();
    render(<PublicClaimList claims={[SUPPORTED]} onSelectPost={onSelectPost} />);

    expect(screen.getByLabelText("Public claims")).toBeInTheDocument();
    const row = screen.getByRole("button", { name: "Open public claim: Public post" });
    expect(row).toHaveTextContent("Organization presence: Public post · Northridge Grid");
    expect(row).toHaveTextContent("Supported");
    expect(row).toHaveTextContent("Public web evidence supports this claim. Open that post.");
    expect(screen.getByRole("link", { name: "https://northridgegrid.example/about" })).toHaveAttribute(
      "href",
      "https://northridgegrid.example/about",
    );

    await userEvent.click(row);
    expect(onSelectPost).toHaveBeenCalledWith("post-demo-public");
  });

  it("keeps unavailable search guidance without inventing a URL", () => {
    render(
      <PublicClaimList
        claims={[
          {
            ...SUPPORTED,
            status_code: "claim_unavailable",
            external_evidence_urls: [],
            next_action:
              "Web verification is unavailable until the search service is connected. Open that post.",
          },
        ]}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "Web verification is unavailable until the search service is connected. Open that post.",
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("renders nothing when no authorized claim is present", () => {
    const { container } = render(<PublicClaimList claims={[]} onSelectPost={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

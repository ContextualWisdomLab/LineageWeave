import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PublicClaimVerdict } from "../api";
import { setLocale } from "../i18n";
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

afterEach(() => setLocale("en"));

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
            claim_kind_code: "claim_public_event",
            status_code: "claim_unavailable",
            external_evidence_urls: [],
            next_action:
              "Public web verification is unavailable. Open that post or try verification again later.",
          },
        ]}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "Public web verification is unavailable. Open that post or try verification again later.",
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("formats a public-event next action after locale lookup", () => {
    setLocale("ko");
    render(
      <PublicClaimList
        claims={[{
          ...SUPPORTED,
          claim_kind_code: "claim_public_event",
          status_code: "claim_unavailable",
          source_post_title: "합성 공개 글",
          external_evidence_urls: [],
          next_action: "Public claim is on 합성 공개 글. Open that post.",
        }]}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "공개 주장은 합성 공개 글에 있습니다. 그 글을 여세요.",
    );
  });

  it("keeps unknown contract codes out of customer copy", () => {
    render(
      <PublicClaimList
        claims={[{
          ...SUPPORTED,
          claim_kind_code: "claim_future_kind",
          status_code: "claim_future_status",
        }]}
        onSelectPost={vi.fn()}
      />,
    );

    const row = screen.getByRole("button");
    expect(row).toHaveTextContent("Recorded claim");
    expect(row).toHaveTextContent("Status unavailable");
    expect(row).not.toHaveTextContent("claim_future_kind");
    expect(row).not.toHaveTextContent("claim_future_status");
  });

  it("renders nothing when no authorized claim is present", () => {
    const { container } = render(<PublicClaimList claims={[]} onSelectPost={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

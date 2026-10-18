import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PublicClaimVerification } from "./PublicClaimVerification";

describe("PublicClaimVerification", () => {
  it("links only absolute HTTP(S) evidence URLs", () => {
    render(
      <PublicClaimVerification
        claims={[{
          claim_text: "Synthetic claim",
          claim_kind: "organization",
          status_code: "claim_supported",
          rationale: "Synthetic rationale",
          source_post_ids: ["synthetic-post"],
          evidence: [
            { title: "Safe source", url: "https://example.test/source", snippet: "Public evidence" },
            { title: "Unsafe source", url: "javascript:alert(1)", snippet: "Untrusted evidence" },
            { title: "Safe source", url: "https://example.test/source", snippet: "Repeated evidence" },
          ],
        }]}
      />,
    );

    expect(screen.getAllByRole("link", { name: "Safe source" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Safe source" })[0]).toHaveAttribute(
      "href",
      "https://example.test/source",
    );
    expect(screen.queryByRole("link", { name: "Unsafe source" })).not.toBeInTheDocument();
    expect(screen.getByText("Unsafe source")).toBeInTheDocument();
  });
});

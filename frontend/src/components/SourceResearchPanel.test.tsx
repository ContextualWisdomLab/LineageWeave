import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SourceResearchPanel } from "./SourceResearchPanel";

const nextAction =
  "Open the cited public resource, then compare it with this post's source unit or image region.";

describe("SourceResearchPanel", () => {
  it("opens a cited public resource without following a javascript URL", async () => {
    const onResearch = vi.fn();
    render(
      <SourceResearchPanel
        canResearch
        onResearch={onResearch}
        citations={[
          {
            lead_kind_code: "research_lead_semantic_unit",
            lead_source_unit_id: "unit-1",
            lead_image_region_id: null,
            lead_excerpt_text: "Demo Corp delayed Apollo.",
            search_query_text: "Demo Corp delayed Apollo.",
            evidence_url: "https://example.com/apollo",
            evidence_title_text: "Public Apollo evidence",
            evidence_excerpt_text: "The published notice describes the delay.",
            judgment_code: "research_supported",
            rationale_text: "The retrieved page matches this source unit.",
            next_action_text: nextAction,
          },
          {
            lead_kind_code: "research_lead_image_region",
            lead_source_unit_id: null,
            lead_image_region_id: "region-1",
            lead_excerpt_text: "Nameplate",
            search_query_text: "Nameplate",
            evidence_url: "javascript:alert(1)",
            evidence_title_text: "unsafe",
            evidence_excerpt_text: null,
            judgment_code: "research_refuted",
            rationale_text: "ignored",
            next_action_text: nextAction,
          },
        ]}
      />,
    );
    expect(screen.getByRole("link", { name: "Public Apollo evidence" })).toHaveAttribute(
      "href",
      "https://example.com/apollo",
    );
    expect(screen.queryByRole("link", { name: "unsafe" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Research public sources" }));
    expect(onResearch).toHaveBeenCalledOnce();
  });

  it("explains a private post without a research action", () => {
    render(
      <SourceResearchPanel
        citations={[]}
        unavailableReason="Private posts cannot send source content to public search."
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Private posts cannot send source content to public search.",
    );
    expect(screen.queryByRole("button", { name: "Research public sources" })).not.toBeInTheDocument();
  });
});

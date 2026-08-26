import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { SourceResearchPanel } from "./SourceResearchPanel";

const meta = {
  title: "Post/Source research",
  component: SourceResearchPanel,
} satisfies Meta<typeof SourceResearchPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

const nextAction =
  "Open the cited public resource, then compare it with the highlighted passage or image detail from this post.";

export const SupportedAndUnavailable: Story = {
  args: {
    canResearch: true,
    citations: [
      {
        lead_kind_code: "research_lead_semantic_unit",
        lead_source_unit_id: "unit-1",
        lead_image_region_id: null,
        lead_excerpt_text: "Demo Corp delayed the Apollo transformer shipment.",
        search_query_text: "Demo Corp delayed the Apollo transformer shipment.",
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
        lead_excerpt_text: "Nameplate Apollo 500 kVA",
        search_query_text: "Nameplate Apollo 500 kVA",
        evidence_url: null,
        evidence_title_text: null,
        evidence_excerpt_text: null,
        judgment_code: "research_unavailable",
        rationale_text: "No usable public resource could be retrieved from search results.",
        next_action_text: nextAction,
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Supported by a cited public resource")).toBeVisible();
    await expect(canvas.getByText("Public research unavailable")).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Public Apollo evidence" })).toHaveAttribute(
      "rel",
      "noreferrer",
    );
    await expect(canvas.getByRole("button", { name: "Research public sources" })).toBeEnabled();
  },
};

export const PrivatePost: Story = {
  args: {
    citations: [],
    unavailableReason: "Public research is unavailable for this post. Review its existing evidence instead.",
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("status"),
    ).toHaveTextContent("Public research is unavailable for this post. Review its existing evidence instead.");
  },
};

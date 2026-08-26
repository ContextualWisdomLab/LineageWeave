import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { PublicClaimVerification } from "./PublicClaimVerification";

const meta = {
  title: "Ask Agent/Public claim verification",
  component: PublicClaimVerification,
} satisfies Meta<typeof PublicClaimVerification>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ThreeWayStatus: Story = {
  args: {
    claims: [
      {
        claim_text: "project: Apollo",
        claim_kind: "semantic_project",
        status_code: "claim_supported",
        rationale: "A public source supports this claim.",
        source_post_ids: ["synthetic-post-1"],
        evidence: [{
          title: "Public Apollo evidence",
          url: "https://example.com/apollo",
          snippet: "Apollo is described as a project.",
        }],
      },
      {
        claim_text: "Demo relation",
        claim_kind: "knowledge_graph_relation",
        status_code: "claim_refuted",
        rationale: "The selected public source conflicts with this claim.",
        source_post_ids: ["synthetic-post-2"],
        evidence: [{
          title: "Public relation evidence",
          url: "https://example.org/relation",
          snippet: "The published relation has the opposite direction.",
        }],
      },
      {
        claim_text: "ontology_reference: Example",
        claim_kind: "ontology_reference",
        status_code: "claim_not_enough_information",
        rationale: "No selected source establishes the claim.",
        source_post_ids: ["synthetic-post-3"],
        evidence: [],
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Supported by public evidence")).toBeVisible();
    await expect(canvas.getByText("Conflicts with public evidence")).toBeVisible();
    await expect(canvas.getByText("Not enough public information")).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Public Apollo evidence" })).toHaveAttribute(
      "rel",
      "noreferrer",
    );
  },
};

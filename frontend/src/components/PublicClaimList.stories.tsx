import type { Meta, StoryObj } from "@storybook/react-vite";
import { PublicClaimList } from "./PublicClaimList";

const meta = {
  title: "Evidence/PublicClaimList",
  component: PublicClaimList,
  args: {
    onSelectPost: () => undefined,
    claims: [
      {
        public_claim_envelope_id: "env-demo-public",
        source_post_id: "post-demo-public",
        source_post_title: "Public post",
        claim_kind_code: "claim_organization_presence",
        subject_label: "Northridge Grid",
        claim_text: "Northridge Grid is a power utility named on the Demo public post.",
        status_code: "claim_supported",
        external_evidence_urls: ["https://northridgegrid.example/about"],
        next_action: "Public web evidence supports this claim. Open that post.",
      },
    ],
  },
} satisfies Meta<typeof PublicClaimList>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SupportedPresence: Story = {};

export const UnavailableSearch: Story = {
  args: {
    claims: [
      {
        public_claim_envelope_id: "env-demo-public",
        source_post_id: "post-demo-public",
        source_post_title: "Public post",
        claim_kind_code: "claim_organization_presence",
        subject_label: "Northridge Grid",
        claim_text: "Northridge Grid is a power utility named on the Demo public post.",
        status_code: "claim_unavailable",
        external_evidence_urls: [],
        next_action:
          "Web verification is unavailable until the search service is connected. Open that post.",
      },
    ],
  },
};

export const Empty: Story = {
  args: {
    claims: [],
  },
};

import type { Meta, StoryObj } from "@storybook/react-vite";
import { CustomerMaster } from "./CustomerMaster";

const meta = {
  title: "고객 마스터/CustomerMaster",
  component: CustomerMaster,
} satisfies Meta<typeof CustomerMaster>;

export default meta;

type Story = StoryObj<typeof meta>;

export const PendingOntologyAttach: Story = {
  args: {
    me: {
      user_account_id: "acct-1",
      display_name: "Demo Analyst",
      permission_codes: ["post_read"],
      corporate_entities: [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
    },
    orgmetraAvailable: false,
    units: [],
    keymen: [],
    commitments: [],
    pendingAttach: {
      label: "Demo Corp parent candidate",
      evidence_url: "https://example.test/demo-corp",
      status_label: "미검증 후보",
      promote_destination: "customers",
    },
    onAttachPending: () => undefined,
  },
};

export const OrgmetraUnavailable: Story = {
  args: {
    me: {
      user_account_id: "acct-1",
      display_name: "Demo Analyst",
      permission_codes: ["post_read"],
      corporate_entities: [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
    },
    orgmetraAvailable: false,
    units: [],
    keymen: [],
    commitments: [],
  },
};

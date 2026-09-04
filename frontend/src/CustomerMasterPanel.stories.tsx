import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { CustomerMasterPanel } from "./App";
import "./App.css";
import "./index.css";

const customerMaster = {
  corporate_entities: [
    {
      corporate_entity_id: "synthetic-parent",
      corporate_entity_code: "SYN-PARENT",
      entity_name: "Northwind Research",
      entity_level_code: "account",
      entity_level_label: "Account",
      parent_entity_id: "synthetic-child",
    },
    {
      corporate_entity_id: "synthetic-child",
      corporate_entity_code: "SYN-CHILD",
      entity_name: "Northwind Field Office",
      entity_level_code: "affiliate",
      entity_level_label: "Affiliate",
      parent_entity_id: "synthetic-parent",
    },
  ],
  keymen: [],
  source_customer_hints: [],
  source_author_hints: [],
  relationship_network: [],
};

const meta = {
  title: "Workspace/CustomerMasterPanel",
  component: CustomerMasterPanel,
  parameters: { layout: "fullscreen" },
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url.endsWith("/api/me")) {
        return new Response(JSON.stringify({
          user_account_id: "synthetic-member",
          display_name: "Synthetic Reviewer",
          permission_codes: [],
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/customer-master")) {
        return new Response(JSON.stringify(customerMaster), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unexpected synthetic request: ${url}`);
    };
    return () => { globalThis.fetch = previousFetch; };
  },
} satisfies Meta<typeof CustomerMasterPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CyclePreserved: Story = {
  args: { accessToken: "synthetic-token" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.findByText("Northwind Research")).resolves.toBeVisible();
    await expect(canvas.getByText(/Hierarchy link ignored: cycle/)).toBeVisible();
    await expect(canvas.getByText("Northwind Field Office")).toBeVisible();
  },
};

export const CyclePreservedMobile: Story = {
  ...CyclePreserved,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

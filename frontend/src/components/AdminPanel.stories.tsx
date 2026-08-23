import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import type { CurrentUser, TenantConfig } from "../api";
import { AdminPanel } from "./AdminPanel";

const DEMO_TENANT_CONFIG: TenantConfig = {
  brandName: "Demo Corp",
  systemName: "LineageWeave",
  copyrightYear: 2026,
  copyrightHolder: "Demo Corp",
};

const DEMO_CURRENT_USER: CurrentUser = {
  user_account_id: "demo-account",
  display_name: "Demo Analyst",
  permission_codes: ["post_read", "post_admin"],
  account_affiliations: [
    {
      corporate_entity_id: "demo-corp",
      corporate_entity_code: "DEMO",
      entity_name: "Demo Corp",
      process_unit_id: null,
      process_unit_code: null,
      process_unit_name: null,
    },
  ],
};

const meta = {
  title: "Workspace/AdminPanel",
  component: AdminPanel,
  args: {
    currentTenantConfig: DEMO_TENANT_CONFIG,
    onTenantConfigChange: () => undefined,
    accessToken: "demo-token",
    currentUser: DEMO_CURRENT_USER,
    onNavigate: () => undefined,
    onOpenBoardTool: () => undefined,
  },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof AdminPanel>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Admin control center")).toBeInTheDocument();
    await expect(canvas.getByText("10 routes")).toBeInTheDocument();
  },
};

export const AccountScope: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Account scope"));
    await expect(canvas.getByText("Demo Analyst")).toBeInTheDocument();
    await expect(canvas.getByText("post_read, post_admin")).toBeInTheDocument();
  },
};

export const TenantSettings: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Tenant settings"));
    const brandInput = canvas.getByLabelText("Tenant brand name") as HTMLInputElement;
    await expect(brandInput.value).toBe("Demo Corp");
    // Save is deliberately left unclicked -- it performs a real
    // updateTenantConfig() network call, which this story does not mock.
    const saveButton = canvas.getByRole("button", { name: "Save settings" });
    await expect(saveButton).toBeDisabled();
  },
};

export const NoAffiliations: Story = {
  args: {
    currentUser: { ...DEMO_CURRENT_USER, account_affiliations: [] },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Account scope"));
    await expect(canvas.getByText("Not available")).toBeInTheDocument();
  },
};

export const LoadingCurrentUser: Story = {
  args: {
    currentUser: null,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Account scope"));
    await expect(canvas.getByText("Loading...")).toBeInTheDocument();
  },
};

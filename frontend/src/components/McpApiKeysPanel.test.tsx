import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { McpApiKeysPanel } from "./McpApiKeysPanel";
import { createMcpApiKey, fetchMcpApiKeys, revokeMcpApiKey } from "../api";

vi.mock("../api", () => ({
  createMcpApiKey: vi.fn(),
  fetchMcpApiKeys: vi.fn(),
  revokeMcpApiKey: vi.fn(),
}));

const fetchKeys = vi.mocked(fetchMcpApiKeys);
const createKey = vi.mocked(createMcpApiKey);
const revokeKey = vi.mocked(revokeMcpApiKey);

const activeKey = {
  mcp_api_key_id: "key-1",
  display_name: "local client",
  key_prefix: "lw_mcp_",
  created_at: "2026-08-21T00:00:00Z",
  expires_at: null,
  revoked_at: null,
};

describe("McpApiKeysPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchKeys.mockResolvedValue({ api_keys: [] });
  });

  it("requires a label and reveals a created secret only in the creation result", async () => {
    const user = userEvent.setup();
    createKey.mockResolvedValue({ ...activeKey, api_key: "lw_mcp_secret" });
    render(<McpApiKeysPanel accessToken="oidc-token" />);

    await user.click(screen.getByRole("button", { name: "Create key" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Key label is required.");

    await user.type(screen.getByLabelText("Key label"), "local client");
    await user.click(screen.getByRole("button", { name: "Create key" }));
    expect(await screen.findByText("lw_mcp_secret")).toBeInTheDocument();
    expect(screen.getByText("A new key is shown once. Store it before leaving this page.")).toBeInTheDocument();
    expect(createKey).toHaveBeenCalledWith("oidc-token", "local client", null);
  });

  it("revokes an active key and removes the revoke action", async () => {
    const user = userEvent.setup();
    fetchKeys.mockResolvedValue({ api_keys: [activeKey] });
    revokeKey.mockResolvedValue({ ...activeKey, revoked_at: "2026-08-21T01:00:00Z" });
    render(<McpApiKeysPanel accessToken="oidc-token" />);

    await user.click(await screen.findByRole("button", { name: "Revoke" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("MCP key revoked."));
    expect(revokeKey).toHaveBeenCalledWith("oidc-token", "key-1");
    expect(screen.queryByRole("button", { name: "Revoke" })).not.toBeInTheDocument();
  });

  it("sends the selected local calendar date's end as the expiry", async () => {
    const user = userEvent.setup();
    createKey.mockResolvedValue({ ...activeKey, api_key: "lw_mcp_secret" });
    render(<McpApiKeysPanel accessToken="oidc-token" />);

    await user.type(screen.getByLabelText("Key label"), "local client");
    fireEvent.change(screen.getByLabelText("Expires"), { target: { value: "2026-08-21" } });
    await user.click(screen.getByRole("button", { name: "Create key" }));

    expect(createKey).toHaveBeenCalledWith(
      "oidc-token",
      "local client",
      new Date(2026, 7, 21, 23, 59, 59, 999).toISOString(),
    );
  });
});

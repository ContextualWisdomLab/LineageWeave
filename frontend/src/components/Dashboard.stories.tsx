import type { Meta, StoryObj } from "@storybook/react-vite";
import { Dashboard } from "./Dashboard";
import "../App.css";

type Fixture = "loaded" | "empty" | "fallback" | "unavailable" | "loading";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const PROJECT_REPORT = {
  grouping_key: "proj-demo-lineage",
  grouping_label: "Demo Corp lineage rollout",
  selected_model: "gpcm",
  mean_theta: 1.42,
  mean_theta_sd: 0.31,
  post_count: 3,
  item_count: 6,
  fit_converged: true,
  link_method: "free",
  anchor_period_code: null,
  delta_mean_theta: null,
  members: [
    { post_id: "post-1", post_title: "Cutoff valve replacement approved", theta_eap: 1.8, theta_sd: 0.2 },
    { post_id: "post-2", post_title: "Vendor quote reconciled against PO", theta_eap: 1.1, theta_sd: 0.25 },
  ],
  selected_items: [],
  leftover_pairs: [],
};

function installFixture(fixture: Fixture) {
  globalThis.fetch = async (input) => {
    const url = String(input);
    if (fixture === "loading") {
      return new Promise<Response>(() => undefined);
    }
    if (fixture === "unavailable") {
      return jsonResponse({ detail: "unavailable" }, 503);
    }
    if (url.includes("/api/reports/project/")) {
      if (fixture === "empty" || fixture === "fallback") {
        return jsonResponse({ grouping_kind: "project", period_code: "2026-W02", reports: [] });
      }
      return jsonResponse({ grouping_kind: "project", period_code: "2026-W02", reports: [PROJECT_REPORT] });
    }
    if (url.includes("/api/reports/project")) {
      if (fixture === "empty" || fixture === "fallback") {
        return jsonResponse({ grouping_kind: "project", periods: [] });
      }
      return jsonResponse({
        grouping_kind: "project",
        periods: [{ grouping_key: "proj-demo-lineage", period_code: "2026-W02", mean_theta: 1.42, post_count: 3 }],
      });
    }
    if (url.includes("/api/rankings")) {
      if (fixture === "fallback") {
        return jsonResponse({
          port: "rankweave",
          status: "accepted",
          status_reason: null,
          rankings: [
            { post_id: "post-3", post_title: "Ranked by RankWeave only", fused_rank: 1 },
            { post_id: "post-4", post_title: "Second RankWeave hit", fused_rank: 2 },
          ],
        });
      }
      return jsonResponse({ port: "rankweave", status: "unavailable", status_reason: "rankweave_not_available", rankings: [] });
    }
    return jsonResponse({});
  };
}

const meta = {
  title: "Workspace/Dashboard",
  component: Dashboard,
  args: {
    accessToken: "synthetic-story-token",
    onSelectPost: () => undefined,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof Dashboard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loaded: Story = {
  render(args) {
    installFixture("loaded");
    return <Dashboard {...args} />;
  },
};

export const Empty: Story = {
  render(args) {
    installFixture("empty");
    return <Dashboard {...args} />;
  },
};

export const FallbackToRankWeave: Story = {
  render(args) {
    installFixture("fallback");
    return <Dashboard {...args} />;
  },
};

export const Loading: Story = {
  render(args) {
    installFixture("loading");
    return <Dashboard {...args} />;
  },
};

export const Unavailable: Story = {
  render(args) {
    installFixture("unavailable");
    return <Dashboard {...args} />;
  },
};

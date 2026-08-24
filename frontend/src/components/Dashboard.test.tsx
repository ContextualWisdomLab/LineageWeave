import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";

const { fetchPeriodReportIndex, fetchPeriodReports, fetchRankings } = vi.hoisted(() => ({
  fetchPeriodReportIndex: vi.fn(),
  fetchPeriodReports: vi.fn(),
  fetchRankings: vi.fn(),
}));

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchPeriodReportIndex,
  fetchPeriodReports,
  fetchRankings,
}));

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

beforeEach(() => {
  fetchPeriodReportIndex.mockReset();
  fetchPeriodReports.mockReset();
  fetchRankings.mockReset();
  fetchRankings.mockResolvedValue({ port: "rankweave", status: "unavailable", status_reason: "rankweave_not_available", rankings: [] });
});

it("ranks projects and posts by real fast-mlsirm theta, never a literal score", async () => {
  fetchPeriodReportIndex.mockResolvedValue({
    grouping_kind: "project",
    periods: [{ grouping_key: "proj-demo-lineage", period_code: "2026-W02", mean_theta: 1.42, post_count: 3 }],
  });
  fetchPeriodReports.mockResolvedValue({ grouping_kind: "project", period_code: "2026-W02", reports: [PROJECT_REPORT] });

  render(<Dashboard accessToken="token" onSelectPost={() => undefined} />);

  expect(await screen.findByText("Demo Corp lineage rollout")).toBeInTheDocument();
  expect(screen.getByText("fast-mlsirm θ 1.42")).toBeInTheDocument();
  expect(screen.getByText("Cutoff valve replacement approved")).toBeInTheDocument();
  expect(screen.getByText("fast-mlsirm θ 1.80")).toBeInTheDocument();
  expect(fetchPeriodReports).toHaveBeenCalledWith("token", "project", "2026-W02");
});

it("falls back to RankWeave's fused ranking when no project period has been calibrated yet", async () => {
  fetchPeriodReportIndex.mockResolvedValue({ grouping_kind: "project", periods: [] });
  fetchRankings.mockResolvedValue({
    port: "rankweave",
    status: "accepted",
    status_reason: null,
    rankings: [{ post_id: "post-9", post_title: "RankWeave-only hit", fused_rank: 1 }],
  });

  render(<Dashboard accessToken="token" onSelectPost={() => undefined} />);

  expect(await screen.findByText("RankWeave-only hit")).toBeInTheDocument();
  expect(screen.getByText("RankWeave fusion")).toBeInTheDocument();
  expect(fetchPeriodReports).not.toHaveBeenCalled();
  expect(screen.getByText("No calibrated project reports yet. Ask an administrator to run a period-report rebuild.")).toBeInTheDocument();
});

it("shows honest empty-state copy when no signal is available at all", async () => {
  fetchPeriodReportIndex.mockResolvedValue({ grouping_kind: "project", periods: [] });

  render(<Dashboard accessToken="token" onSelectPost={() => undefined} />);

  expect(await screen.findByText("No calibrated project reports yet. Ask an administrator to run a period-report rebuild.")).toBeInTheDocument();
  expect(await screen.findByText("No posts have been evaluated yet. Evaluate a post to surface it here.")).toBeInTheDocument();
});

it("surfaces a retryable error instead of a raw exception when the project index fetch fails", async () => {
  fetchPeriodReportIndex.mockRejectedValueOnce(new TypeError("Cannot read properties of undefined (reading 'periods')"));
  fetchPeriodReportIndex.mockResolvedValueOnce({ grouping_kind: "project", periods: [] });

  render(<Dashboard accessToken="token" onSelectPost={() => undefined} />);

  const alert = await screen.findByRole("alert");
  expect(alert).not.toHaveTextContent(/TypeError|periods/i);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(fetchPeriodReportIndex).toHaveBeenCalledTimes(2));
});

it("opens the clicked post and the top-theta member of a clicked project", async () => {
  fetchPeriodReportIndex.mockResolvedValue({
    grouping_kind: "project",
    periods: [{ grouping_key: "proj-demo-lineage", period_code: "2026-W02", mean_theta: 1.42, post_count: 3 }],
  });
  fetchPeriodReports.mockResolvedValue({ grouping_kind: "project", period_code: "2026-W02", reports: [PROJECT_REPORT] });
  const onSelectPost = vi.fn();

  render(<Dashboard accessToken="token" onSelectPost={onSelectPost} />);

  fireEvent.click(await screen.findByRole("button", { name: "Open post: Cutoff valve replacement approved" }));
  expect(onSelectPost).toHaveBeenCalledWith("post-1");

  fireEvent.click(screen.getByRole("button", { name: "Open project: Demo Corp lineage rollout" }));
  expect(onSelectPost).toHaveBeenCalledWith("post-1");
});

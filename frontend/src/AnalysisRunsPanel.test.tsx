import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisRunsPanel } from "./AnalysisRunsPanel";
import {
  analysisRunCaption,
  analysisRunCorpusHint,
  analysisRunEmptyPostsHint,
  analysisRunNextAction,
  shortDigest,
} from "./analysisRunDisplay";
import type { AnalysisRun } from "./api";

const sampleRun: AnalysisRun = {
  analysis_run_id: "run-demo-lineage",
  run_kind_code: "analysis_run_lineage",
  run_kind_label: "Lineage reconstruction",
  scope_kind_code: "analysis_scope_corporate_entity",
  scope_kind_label: "Corporate entity",
  scope_entity_name: "Demo Corp",
  status_code: "analysis_status_succeeded",
  status_label: "Succeeded",
  knowledge_cutoff: "2026-01-12T12:00:00Z",
  requested_at: "2026-01-12T12:30:00Z",
  source_counts: [],
};

const failedTeppRun: AnalysisRun = {
  analysis_run_id: "run-demo-tepp",
  run_kind_code: "analysis_run_tepp",
  run_kind_label: "TEPP measurement",
  scope_kind_code: "analysis_scope_corporate_entity",
  scope_kind_label: "Corporate entity",
  scope_entity_name: "Demo Corp",
  status_code: "analysis_status_failed",
  status_label: "Failed",
  knowledge_cutoff: "2026-01-12T12:00:00Z",
  requested_at: "2026-01-12T12:34:00Z",
  source_counts: [],
};

describe("analysisRunCaption", () => {
  it("joins kind, status, and scope so the operator knows which run to open", () => {
    expect(analysisRunCaption(sampleRun)).toBe(
      "Lineage reconstruction · Succeeded · Demo Corp",
    );
  });
});

describe("analysisRunNextAction", () => {
  it("tells the operator to open a failed run and reconnect the service", () => {
    expect(analysisRunNextAction(failedTeppRun)).toMatch(/connect the measurement service/);
  });

  it("hides a next action on a succeeded run", () => {
    expect(analysisRunNextAction(sampleRun)).toBeNull();
  });
});

describe("analysisRunEmptyPostsHint", () => {
  it("names TEPP so the empty list is not read as a reconstruction miss", () => {
    expect(analysisRunEmptyPostsHint(failedTeppRun)).toMatch(/for TEPP to measure/);
  });
});

describe("analysisRunCorpusHint", () => {
  it("says cutoff posts are the TEPP measurement bag, not a reconstruction", () => {
    expect(analysisRunCorpusHint(failedTeppRun)).toMatch(/cutoff corpus TEPP would measure/);
  });

  it("stays silent on a lineage run", () => {
    expect(analysisRunCorpusHint(sampleRun)).toBeNull();
  });
});

describe("shortDigest", () => {
  it("returns a 12-character prefix for comparing an approved revision", () => {
    expect(shortDigest("c".repeat(40))).toBe("c".repeat(12));
  });

  it("returns null when a digest is missing so the UI can hide the row", () => {
    expect(shortDigest(undefined)).toBeNull();
  });
});

describe("AnalysisRunsPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tells the operator to open a later run when no posts existed at cutoff", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/analysis-runs/run-demo-lineage")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                ...sampleRun,
                visible_posts: [],
                code_revision_sha: "c".repeat(40),
                configuration_sha256: "b".repeat(64),
              }),
              { status: 200 },
            ),
          );
        }
        if (url.endsWith("/api/analysis-runs")) {
          return Promise.resolve(
            new Response(JSON.stringify({ analysis_runs: [sampleRun] }), { status: 200 }),
          );
        }
        return Promise.resolve(new Response(null, { status: 404 }));
      }),
    );

    render(<AnalysisRunsPanel accessToken="test-access-token" onSelectPost={() => undefined} />);
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Succeeded · Demo Corp",
      }),
    );
    expect(
      await screen.findByText(/No posts were available at this cutoff/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open run post:/ })).not.toBeInTheDocument();
  });

  it("opens a failed TEPP run and shows the machine failure code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/analysis-runs/run-demo-tepp")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                ...failedTeppRun,
                visible_posts: [{ post_id: "post-1", post_title: "Public post" }],
                status_history: [
                  {
                    status_ordinal: 3,
                    status_code: "analysis_status_failed",
                    status_label: "Failed",
                    occurred_at: "2026-01-12T12:37:00Z",
                    failure_code: "tepp_not_available",
                  },
                ],
              }),
              { status: 200 },
            ),
          );
        }
        if (url.endsWith("/api/analysis-runs")) {
          return Promise.resolve(
            new Response(JSON.stringify({ analysis_runs: [failedTeppRun] }), { status: 200 }),
          );
        }
        return Promise.resolve(new Response(null, { status: 404 }));
      }),
    );

    render(<AnalysisRunsPanel accessToken="test-access-token" onSelectPost={() => undefined} />);
    expect(
      await screen.findByText(/Open this run to see why it failed/),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open analysis run: TEPP measurement · Failed · Demo Corp",
      }),
    );
    expect(await screen.findByText(/Failed 2026-01-12 12:37 · tepp_not_available/)).toBeInTheDocument();
    expect(screen.getByText(/cutoff corpus TEPP would measure/)).toBeInTheDocument();
  });
});

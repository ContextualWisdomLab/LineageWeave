import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisRunsPanel } from "./AnalysisRunsPanel";
import { analysisRunCaption, shortDigest, snapshotCountCaption } from "./analysisRunDisplay";
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
  source_counts: [
    {
      count_type_code: "analysis_count_document",
      count_type_label: "Documents",
      count_value: 3,
    },
  ],
};

describe("analysisRunCaption", () => {
  it("joins kind, status, and scope so the operator knows which run to open", () => {
    expect(analysisRunCaption(sampleRun)).toBe(
      "Lineage reconstruction · Succeeded · Demo Corp",
    );
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

describe("snapshotCountCaption", () => {
  it("names the capture so the badge is not read as the cutoff post list", () => {
    expect(
      snapshotCountCaption({
        count_type_code: "analysis_count_document",
        count_type_label: "Documents",
        count_value: 3,
      }),
    ).toBe("3 documents in the snapshot");
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
    expect(screen.getAllByText("3 documents in the snapshot").length).toBeGreaterThan(0);
  });

  it("opens only in-cutoff titles and never a later own-corp post", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/analysis-runs/run-demo-lineage")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                ...sampleRun,
                visible_posts: [{ post_id: "post-demo-public", post_title: "Demo public post" }],
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
      await screen.findByRole("button", { name: "Open run post: Demo public post" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Late Demo public post/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/No posts were available at this cutoff/)).not.toBeInTheDocument();
  });
});

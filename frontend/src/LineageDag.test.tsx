import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";
import { setLocale } from "./i18n";

const graph: LineageGraph = {
  nodes: [
    {
      id: "post-a",
      group: "Apollo",
      label: "Initial event",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "post-b",
      group: "Apollo",
      label: "Follow-up event",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "post-a",
      target: "post-b",
      fused_score: 0.685,
      channel_scores: {
        temporal: 0.9,
        secondary_key: 1,
        text: 0.42,
      },
      channel_evidence: [
        {
          signal_code: "secondary_key",
          signal_label: "Secondary key",
          score: 1,
          weight: 0.25,
          contribution: 0.25,
          rank: 1,
        },
        {
          signal_code: "temporal",
          signal_label: "Time proximity",
          score: 0.9,
          weight: 0.25,
          contribution: 0.225,
          rank: 2,
        },
        {
          signal_code: "text",
          signal_label: "Text similarity",
          score: 0.42,
          weight: 0.5,
          contribution: 0.21,
          rank: 3,
        },
      ],
      reconstruction_version: "rankweave-weighted-convex-v1",
      reconstructed_at: "2026-08-20T04:00:00+00:00",
    },
  ],
};

describe("LineageDag evidence disclosure", () => {
  beforeEach(() => {
    setLocale("en");
  });

  it("renders ranked exact score, weight, and contribution values", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const disclosure = screen.getByText(
      /Follow-up event.*Initial event.*0\.6850/,
      { selector: "summary" },
    );
    expect(disclosure.closest("details")).toHaveAttribute("open");

    const table = screen.getByRole("table", { name: "Lineage evidence scores" });
    expect(
      within(table).getByRole("row", {
        name: /1 Secondary-key match 1\.0000 0\.2500 0\.2500/,
      }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("row", {
        name: /2 Time proximity 0\.9000 0\.2500 0\.2250/,
      }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("row", {
        name: /3 Text similarity 0\.4200 0\.5000 0\.2100/,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/rankweave-weighted-convex-v1/)).toBeInTheDocument();
    expect(screen.getByText(/2026-08-20T04:00:00\+00:00/)).toBeInTheDocument();
  });

  it("labels inference as non-causal and makes absent LLM participation explicit", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(
      screen.getByText("This connection is inferred evidence, not a causal fact."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No LLM adjudication participated in this connection."),
    ).toBeInTheDocument();
    expect(screen.queryByText("0.0000")).not.toBeInTheDocument();
  });

  it("includes the same weighted evidence in the SVG edge description", () => {
    const { container } = render(
      <LineageDag graph={graph} onSelectPost={vi.fn()} />,
    );

    const edgeTitle = container.querySelector(".lineage-dag-edge title");
    expect(edgeTitle?.textContent).toContain("Follow-up event follows Initial event");
    expect(edgeTitle?.textContent).toContain("Fused score 0.6850");
    expect(edgeTitle?.textContent).toContain(
      "Secondary-key match 1.0000 × 0.2500 = 0.2500",
    );
    expect(edgeTitle?.textContent).toContain(
      "Time proximity 0.9000 × 0.2500 = 0.2250",
    );
    expect(edgeTitle?.textContent).not.toContain("LLM adjudication 0.0000");
  });

  it("localizes signal labels from stable signal codes instead of backend English", () => {
    setLocale("ko");
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const table = screen.getByRole("table", { name: "계보 근거 점수" });
    expect(within(table).getByText("보조 키 일치")).toBeInTheDocument();
    expect(within(table).getByText("시간 근접도")).toBeInTheDocument();
    expect(within(table).getByText("텍스트 유사도")).toBeInTheDocument();
    expect(within(table).queryByText("Secondary key")).not.toBeInTheDocument();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchProjectHistory } from "../api";
import type { ProjectHistoryProjection } from "../projectHistory";
import { AskProjectHistoryLinks } from "./AskProjectHistoryLinks";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    fetchProjectHistory: vi.fn(),
  };
});

const projection: ProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Synthetic renewal",
  focus_event_id: "post-voc",
  time_basis_code: "source_post_created_at_fallback",
  knowledge_cutoff: "2026-08-20T12:00:00Z",
  evidence_boundary_code: "authorized_visible_source_posts",
  event_count: 1,
  connected_post_count: 0,
  lineage_count: 0,
  distinct_actor_count: 0,
  distinct_observed_actor_count: 0,
  truncated: false,
  events: [
    {
      event_id: "post-voc",
      source_post_id: "post-voc",
      event_title: "Synthetic VOC received",
      event_type_code: "voc_received",
      event_type_basis_code: "display_classification",
      occurred_at: "2026-02-02T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: "voc",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      responsibility_evidence: [],
      observed_responsibilities: [],
      responsibility_transition_code: null,
      responsibility_transition_truth_status_code: null,
      related_prior_paths: [],
    },
  ],
};

const link = {
  project_key: "P-100",
  project_name: "Synthetic renewal",
  focus_post_id: "post-voc",
  source_post_ids: ["post-voc"],
  knowledge_cutoff: "2026-08-20T12:00:00Z",
  truth_status_code: "observed" as const,
};

describe("AskProjectHistoryLinks", () => {
  beforeEach(() => {
    vi.mocked(fetchProjectHistory).mockReset();
  });

  it("loads the canonical timeline at the answer cutoff and preserves source navigation", async () => {
    const onOpenPost = vi.fn();
    vi.mocked(fetchProjectHistory).mockResolvedValue(projection);

    render(
      <AskProjectHistoryLinks
        accessToken="token"
        links={[link]}
        truncated={false}
        onOpenPost={onOpenPost}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /open project history: Synthetic renewal/i }));

    await waitFor(() => {
      expect(fetchProjectHistory).toHaveBeenCalledWith(
        "token",
        "P-100",
        "2026-08-20T12:00:00Z",
        "post-voc",
      );
    });
    expect(screen.getByRole("heading", { name: /project event timeline/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /open source record: Synthetic VOC received/i }));
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });

  it("reports truncation and leaves the answer readable when the timeline fetch fails", async () => {
    vi.mocked(fetchProjectHistory).mockRejectedValue(new Error("synthetic failure"));

    render(
      <AskProjectHistoryLinks
        accessToken="token"
        links={[link]}
        truncated
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/additional cited projects are not shown/i);
    fireEvent.click(screen.getByRole("button", { name: /open project history: Synthetic renewal/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/project history could not be loaded/i);
    expect(screen.getByText("Synthetic renewal")).toBeInTheDocument();
  });

  it("renders nothing when the answer cites no project identity", () => {
    const { container } = render(
      <AskProjectHistoryLinks
        accessToken="token"
        links={[]}
        truncated={false}
        onOpenPost={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

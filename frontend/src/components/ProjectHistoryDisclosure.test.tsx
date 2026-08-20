import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectHistoryDisclosure } from "./ProjectHistoryDisclosure";

const projection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Northridge renewal",
  focus_event_id: "voc",
  time_basis_code: "document_time",
  event_count: 1,
  distinct_observed_actor_count: 0,
  truncated: false,
  events: [
    {
      event_id: "voc",
      source_post_id: "post-voc",
      event_title: "VOC received",
      event_type_code: "voc_received",
      event_type_basis_code: "display_classification",
      occurred_at: "2026-07-30T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "voc",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [],
      responsibility_transition_code: null,
      related_prior_paths: [],
    },
  ],
};

afterEach(() => vi.unstubAllGlobals());

describe("ProjectHistoryDisclosure", () => {
  it("loads the ABAC endpoint only after the buyer opens the project history", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(projection), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onSearch = vi.fn();
    render(
      <ProjectHistoryDisclosure
        accessToken="token-1"
        projectKey="P-100"
        focusPostId="post-voc"
        knowledgeCutoff="2026-08-01T00:00:00Z"
        onOpenPost={vi.fn()}
        onSearch={onSearch}
      />,
    );

    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Search related posts" }));
    expect(onSearch).toHaveBeenCalledWith("P-100");
    fireEvent.click(screen.getByRole("button", { name: "Open project history" }));

    await screen.findByRole("heading", { name: "Project event timeline" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/project-history?");
    expect(String(url)).toContain("project_key=P-100");
    expect(String(url)).toContain("focus_post_id=post-voc");
    expect(String(url)).toContain("knowledge_cutoff=2026-08-01T00%3A00%3A00Z");
    expect(init.headers.Authorization).toBe("Bearer token-1");
  });

  it("uses one non-leaking unavailable message for hidden, absent, and failed histories", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));
    render(
      <ProjectHistoryDisclosure
        accessToken="token-1"
        projectKey="P-100"
        focusPostId="hidden-post"
        onOpenPost={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open project history" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Project history is unavailable for this evidence.",
      ),
    );
    expect(screen.queryByText(/hidden|forbidden|not found/i)).not.toBeInTheDocument();
  });
});

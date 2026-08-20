import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { setLocale } from "../i18n";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";
import type { TeppProjectHistory } from "../api";

const history: TeppProjectHistory = {
  contract_version: 1,
  project_key: "project-alpha",
  project_name: "Project Alpha",
  focus_event_id: "event-voc",
  inference_status: "temporal_association_only",
  participant_count: 2,
  history_span_start: "2022-03-01T00:00:00Z",
  history_span_end: "2026-06-01T00:00:00Z",
  events: [
    {
      event_id: "event-contract",
      event_type_code: "contract_awarded",
      event_title: "Contract awarded",
      event_time: "2022-03-01T00:00:00Z",
      available_at: "2022-03-01T00:00:00Z",
      availability_basis: "source_post.created_at",
      source_post_id: "post-contract",
      evidence_text: "The order was awarded.",
      actor_ids: ["actor-sales"],
    },
    {
      event_id: "event-voc",
      event_type_code: "voc_received",
      event_title: "VOC received",
      event_time: "2026-06-01T00:00:00Z",
      available_at: "2026-06-01T00:00:00Z",
      availability_basis: "source_post.created_at",
      source_post_id: "post-voc",
      evidence_text: "A customer VOC was registered.",
      actor_ids: ["actor-sales", "actor-customer"],
    },
  ],
  findings: [
    {
      finding_code: "contract_award_before_focus",
      summary:
        "An explicit contract-award event precedes the focus event. This is a temporal association, not a causal conclusion.",
      related_event_ids: ["event-contract", "event-voc"],
      evidence_post_ids: ["post-contract", "post-voc"],
    },
  ],
};

afterEach(() => setLocale("en"));

describe("ProjectHistoryTimeline localization", () => {
  it("renders English Buyer copy and event labels under the English locale", () => {
    setLocale("en");
    render(<ProjectHistoryTimeline history={history} onOpenPost={() => undefined} />);

    expect(screen.getByText("TEPP-connected answer")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project event timeline" })).toBeInTheDocument();
    expect(screen.getByText("Contract award")).toBeInTheDocument();
    expect(screen.getByText("VOC received")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Event details" })).toBeInTheDocument();
    expect(screen.getByText(/TEPP explains temporal associations only/)).toBeInTheDocument();
  });

  it("renders Korean Buyer copy and event labels under the Korean locale", () => {
    setLocale("ko");
    render(<ProjectHistoryTimeline history={history} onOpenPost={() => undefined} />);

    expect(screen.getByText("TEPP 연계 응답")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "프로젝트 이벤트 타임라인" })).toBeInTheDocument();
    expect(screen.getByText("수주")).toBeInTheDocument();
    expect(screen.getByText("VOC 접수")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "이벤트 상세" })).toBeInTheDocument();
  });
});

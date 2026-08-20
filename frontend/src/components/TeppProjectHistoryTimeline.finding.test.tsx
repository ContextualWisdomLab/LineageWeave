import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { setLocale } from "../i18n";
import type { TeppProjectHistory } from "../api";
import { TeppProjectHistoryTimeline } from "./TeppProjectHistoryTimeline";

const history: TeppProjectHistory = {
  contract_version: 1,
  project_key: "project-alpha",
  project_name: "Project Alpha",
  focus_event_id: "event-voc",
  knowledge_cutoff: "2026-08-19T00:00:00Z",
  inference_status: "temporal_association_only",
  participant_count: 2,
  history_span_start: "2023-06-01T00:00:00Z",
  history_span_end: "2026-06-01T00:00:00Z",
  events: [
    {
      event_id: "event-spec",
      event_type_code: "specification_changed",
      event_title: "Specification changed",
      occurred_at: "2023-06-01T00:00:00Z",
      available_at: "2023-06-01T00:00:00Z",
      source_post_id: "post-spec",
      evidence_text: "The specification changed.",
      actor_ids: ["actor-engineering"],
    },
    {
      event_id: "event-voc",
      event_type_code: "voc_received",
      event_title: "VOC received",
      occurred_at: "2026-06-01T00:00:00Z",
      available_at: "2026-06-01T00:00:00Z",
      source_post_id: "post-voc",
      evidence_text: "A customer VOC was registered.",
      actor_ids: ["actor-engineering", "actor-customer"],
    },
  ],
  findings: [
    {
      finding_code: "specification_change_before_focus",
      summary:
        "An explicit specification-change event precedes the focus event. This is a temporal association, not a causal conclusion.",
      related_event_ids: ["event-spec", "event-voc"],
      evidence_post_ids: ["post-spec", "post-voc"],
    },
  ],
};

afterEach(() => setLocale("en"));

describe("TeppProjectHistoryTimeline finding copy", () => {
  it("renders a Korean non-causal explanation from the versioned finding code", () => {
    setLocale("ko");
    render(<TeppProjectHistoryTimeline history={history} onOpenPost={() => undefined} />);

    expect(
      screen.getByText(
        "명시적인 사양 변경 이벤트가 현재 이벤트보다 앞섭니다. 이는 시간적 연관이며 인과 결론이 아닙니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "An explicit specification-change event precedes the focus event. This is a temporal association, not a causal conclusion.",
      ),
    ).not.toBeInTheDocument();
  });
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProjectHistory } from "../api";
import { setLocale } from "../i18n";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const history: ProjectHistory = {
  project_key: "P-1042",
  project_name: "OO Transformer",
  events: [
    {
      project_history_event_id: "order",
      event_type_code: "project_event_order",
      event_type_label: "Order awarded",
      event_title: "Order awarded",
      occurred_at: "2022-03-14T09:00:00Z",
      ended_at: null,
      evidence_post_id: "post-order",
      evidence_post_title: "Order source",
      ontology_iri: "https://example.test/OrderAwardEvent",
      evidence_count: 1,
    },
    {
      project_history_event_id: "spec",
      event_type_code: "project_event_spec_change",
      event_type_label: "Specification changed",
      event_title: "Specification revision approved",
      occurred_at: "2023-06-01T09:00:00Z",
      ended_at: null,
      evidence_post_id: "post-spec",
      evidence_post_title: "Specification source",
      ontology_iri: "https://example.test/SpecificationChangeEvent",
      evidence_count: 1,
    },
    {
      project_history_event_id: "voc",
      event_type_code: "project_event_voc",
      event_type_label: "VOC received",
      event_title: "Insulation performance VOC",
      occurred_at: "2026-02-03T09:00:00Z",
      ended_at: null,
      evidence_post_id: "post-voc",
      evidence_post_title: "VOC source",
      ontology_iri: "https://example.test/VoiceOfCustomerEvent",
      evidence_count: 1,
    },
  ],
  relations: [
    {
      source_project_history_event_id: "spec",
      target_project_history_event_id: "voc",
      relation_type_code: "project_relation_related_to",
      relation_type_label: "Related to",
      evidence_post_id: "post-voc",
      evidence_post_title: "VOC source",
      relation_confidence: null,
      causal: false,
    },
  ],
  responsibility_assignments: [
    {
      project_responsibility_assignment_id: "assign-sales",
      cataloged_person_id: "person-sales",
      person_name: "Synthetic Sales Owner",
      responsibility_role_code: "project_role_sales",
      responsibility_role_label: "Sales",
      valid_from: "2022-03-01T00:00:00Z",
      valid_to: "2023-05-20T00:00:00Z",
      evidence_post_id: "post-order",
      evidence_post_title: "Order source",
    },
    {
      project_responsibility_assignment_id: "assign-pm",
      cataloged_person_id: "person-pm",
      person_name: "Synthetic Project Manager",
      responsibility_role_code: "project_role_project_manager",
      responsibility_role_label: "Project manager",
      valid_from: "2023-06-01T00:00:00Z",
      valid_to: null,
      evidence_post_id: "post-spec",
      evidence_post_title: "Specification source",
    },
  ],
  handover_gaps: [
    {
      previous_assignment_id: "assign-sales",
      next_assignment_id: "assign-pm",
      gap_start: "2023-05-20T00:00:00Z",
      gap_end: "2023-06-01T00:00:00Z",
      gap_days: 12,
      gap_basis: "visible_assignment_evidence",
    },
  ],
  truncated: false,
  evidence_boundary: "authorized_source_posts_only",
};

describe("ProjectHistoryTimeline", () => {
  beforeEach(() => {
    setLocale("ko");
  });

  it("selects the current VOC and supports keyboard inspection of an earlier event", async () => {
    const user = userEvent.setup();
    render(<ProjectHistoryTimeline history={history} currentPostId="post-voc" />);

    const voc = screen.getByRole("button", {
      name: /VOC received: Insulation performance VOC/,
    });
    expect(voc).toHaveAttribute("aria-pressed", "true");

    const specification = screen.getByRole("button", {
      name: /Specification changed: Specification revision approved/,
    });
    specification.focus();
    await user.keyboard("{Enter}");

    expect(
      screen.getByRole("region", { name: "선택 이벤트" }),
    ).toHaveTextContent("Specification revision approved");
  });

  it("labels relations as non-causal and opens exact evidence", async () => {
    const onOpenPost = vi.fn();
    render(
      <ProjectHistoryTimeline
        history={history}
        currentPostId="post-voc"
        onOpenPost={onOpenPost}
      />,
    );

    const detail = screen.getByRole("region", { name: "선택 이벤트" });
    expect(detail).toHaveTextContent("연관 관계이며 원인으로 판정하지 않습니다.");
    expect(detail).not.toHaveTextContent("원인이 됩니다");

    await userEvent.click(
      within(detail).getByRole("button", { name: /원문 열기: VOC source/ }),
    );
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });

  it("exposes the visible-evidence handover gap and assignment evidence", async () => {
    const onOpenPost = vi.fn();
    render(<ProjectHistoryTimeline history={history} onOpenPost={onOpenPost} />);

    expect(
      screen.getByRole("note", { name: "인수인계 근거 공백: 12.0 일" }),
    ).toBeVisible();

    await userEvent.click(
      screen.getByRole("button", { name: /Synthetic Sales Owner, Sales/ }),
    );
    expect(onOpenPost).toHaveBeenCalledWith("post-order");
  });

  it("renders an evidence-safe empty state", () => {
    render(
      <ProjectHistoryTimeline
        history={{
          ...history,
          events: [],
          relations: [],
          responsibility_assignments: [],
          handover_gaps: [],
        }}
      />,
    );

    expect(
      screen.getByText("이 프로젝트에 공개할 수 있는 이력 근거가 아직 없습니다."),
    ).toBeVisible();
  });
});

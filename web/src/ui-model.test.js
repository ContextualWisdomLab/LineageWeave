import { describe, expect, it } from "vitest";

import {
  canPreviewAsset,
  counterpartVocExcerpts,
  customerTreeRows,
  emailValidationMessage,
  EMPTY_EMAIL_MESSAGE,
  formatNumber,
  INVALID_EMAIL_MESSAGE,
  isInspectableAsset,
  knowledgeEdgeRows,
  lineageRelationLabel,
  parseSide,
  partitionLineageBeads,
  semanticValue,
  sideLabel,
  sideRows,
  sideText,
  visibilityLabel,
} from "./ui-model.js";

describe("emailValidationMessage", () => {
  it("distinguishes missing, malformed, and usable work email input", () => {
    expect(emailValidationMessage("", true)).toBe(EMPTY_EMAIL_MESSAGE);
    expect(emailValidationMessage("member@example.com", false)).toBe(INVALID_EMAIL_MESSAGE);
    expect(emailValidationMessage("member@example.com", true)).toBe("");
  });
});

describe("counterpartVocExcerpts", () => {
  it("prefers excerpts that name a counterpart and otherwise keeps authorized appointment text", () => {
    const appointments = [
      { appointment_id: "a1", excerpt: "Ada West confirmed the delay", label: "follow-up", occurred_on: "2026-08-01" },
      { appointment_id: "a2", excerpt: "Internal standup notes", occurred_on: "2026-08-02" },
      { appointment_id: "a3", excerpt: "", occurred_on: "2026-08-03" },
    ];
    expect(counterpartVocExcerpts(appointments, [{ person_name: "Ada West" }]).map((item) => item.appointment_id)).toEqual(["a1"]);
    expect(counterpartVocExcerpts(appointments, [{ person_name: "Priya Nair" }]).map((item) => item.appointment_id)).toEqual(["a1", "a2"]);
    expect(counterpartVocExcerpts(appointments, []).map((item) => item.appointment_id)).toEqual(["a1", "a2"]);
  });
});

describe("Keyman presentation helpers", () => {
  it("normalizes text, editable rows, labels, and pasted rows", () => {
    expect(sideText()).toBe("");
    expect(sideText([
      "Reader",
      { actor_type: "team", actor_name: "Design", organization_name: "North", rank: "Lead", title: "Owner" },
      { actor_type: "team", actor_name: "Ops", grade: "M", position: "Manager" },
      { actor_type: "team", actor_name: "Bare" },
      { person_name: "Kim", org_name: "South", grade: "M", position: "Manager" },
      {},
    ])).toBe("Reader\nteam | Design | North | Lead | Owner\nteam | Ops |  | M | Manager\nteam | Bare\nKim | South | M | Manager");

    expect(sideRows()).toEqual([]);
    expect(sideRows([
      "Reader",
      { actor_type: "organization", actor_name: "North", org_name: "North", rank: "", title: "" },
      { actor_type: "team", actor_name: "Design", organization_name: "North", job_title: "Lead" },
      { person_name: "Kim", org: "South", grade: "M", position: "Manager" },
      { org_name: "Fallback org" },
      {},
    ])).toEqual([
      { actor_type: "person", actor_name: "Reader", person_name: "Reader", org_name: "", rank: "", title: "" },
      { actor_type: "organization", actor_name: "North", person_name: "", org_name: "North", organization_name: "North", rank: "", title: "" },
      { actor_type: "team", actor_name: "Design", person_name: "", org_name: "", organization_name: "North", rank: "", title: "Lead" },
      { actor_type: "person", actor_name: "Kim", person_name: "Kim", org_name: "South", organization_name: "South", rank: "M", title: "Manager" },
      { actor_type: "organization", actor_name: "Fallback org", person_name: "", org_name: "Fallback org", organization_name: "Fallback org", rank: "", title: "" },
    ]);

    expect(sideLabel({ actor_type: "organization", actor_name: "North", organization_name: "North", rank: "", title: "" })).toBe("North");
    expect(sideLabel({ actor_type: "person", person_name: "Kim", org_name: "South", rank: "M", title: "Manager" })).toBe("Kim · South · M · Manager");
    expect(sideLabel({ actor_type: "person", actor_name: "Fallback" })).toBe("Fallback");

    expect(parseSide("organization | North | Group | Owner | Lead\nKim | South | M | Manager | Project\n\n팀 | Design | North | Lead")).toEqual([
      { actor_type: "organization", actor_name: "North", organization_name: "Group", org_name: "Group", rank: "Owner", title: "Lead" },
      { person_name: "Kim", org_name: "South", rank: "M", title: "Manager|Project" },
      { actor_type: "team", actor_name: "Design", organization_name: "North", org_name: "North", rank: "Lead", title: "" },
    ]);
  });
});

describe("safe view values", () => {
  it("formats values and restricts previewable assets", () => {
    expect(formatNumber()).toBe("0");
    expect(formatNumber(12345)).toBe("12,345");
    expect(visibilityLabel("public")).toBe("공개");
    expect(visibilityLabel("PRIVATE")).toBe("내부");
    expect(visibilityLabel("unknown")).toBe("공개 범위 확인");
    expect(visibilityLabel()).toBe("공개 범위 확인");
    expect(isInspectableAsset()).toBe(false);
    expect(isInspectableAsset({ inspection_eligible: 1 })).toBe(true);
    expect(canPreviewAsset()).toBe(false);
    expect(canPreviewAsset({ mime_type: "text/plain", encoded_bytes: 1 })).toBe(false);
    expect(canPreviewAsset({ mime_type: "image/png" })).toBe(true);
    expect(canPreviewAsset({ mime_type: "image/png", encoded_bytes: 8 * 1024 * 1024 })).toBe(true);
    expect(canPreviewAsset({ mime_type: "image/png", encoded_bytes: 9 * 1024 * 1024 })).toBe(false);
    expect(semanticValue()).toBe("");
    expect(semanticValue(null)).toBe("");
    expect(semanticValue("")).toBe("");
    expect(semanticValue("term")).toBe("term");
    expect(semanticValue({ term: "value" })).toBe('{"term":"value"}');
  });
});

describe("event lineage presentation", () => {
  it("labels a shared thread as relatedness instead of a sequence", () => {
    expect(lineageRelationLabel("shared_thread_identifier")).toBe("같은 스레드 단서");
    expect(lineageRelationLabel("topic_affinity")).toBe("topic_affinity");
    expect(lineageRelationLabel()).toBe("관련성");
  });

  it("keeps only explicitly connected events in a sequence", () => {
    const first = { evidence_id: "one", connects_to_next: true };
    const second = { evidence_id: "two", connects_to_next: false };
    const third = { evidence_id: "three", connects_to_next: false };
    expect(partitionLineageBeads([first, second, third])).toEqual({
      segments: [[first, second]],
      observations: [third],
    });
    expect(partitionLineageBeads([{ evidence_id: "only", connects_to_next: true }])).toEqual({
      segments: [],
      observations: [{ evidence_id: "only", connects_to_next: true }],
    });
    expect(partitionLineageBeads([
      { evidence_id: "open", connects_to_next: true },
      { evidence_id: "close", connects_to_next: true },
    ])).toEqual({
      segments: [[
        { evidence_id: "open", connects_to_next: true },
        { evidence_id: "close", connects_to_next: true },
      ]],
      observations: [],
    });
    expect(partitionLineageBeads([undefined])).toEqual({ segments: [], observations: [undefined] });
    expect(partitionLineageBeads(null)).toEqual({ segments: [], observations: [] });
  });
});

describe("knowledge graph relationship presentation", () => {
  it("keeps each valid directed relationship with its entity types and evidence", () => {
    expect(knowledgeEdgeRows({
      nodes: [
        { id: "person-1", label: "Reader", type: "person" },
        { id: "event-1", label: "Meeting", type: "event" },
      ],
      edges: [{
        source: "person-1",
        target: "event-1",
        relation: "cross_pu_transaction",
        evidence_status: "observed",
      }],
    })).toEqual([{
      evidenceLabel: "관측 근거",
      relation: "cross_pu_transaction",
      relationLabel: "같은 회사·다른 PU 간 거래",
      sourceLabel: "Reader",
      sourceType: "person",
      sourceTypeLabel: "사람",
      targetLabel: "Meeting",
      targetType: "event",
      targetTypeLabel: "이벤트",
    }]);
  });

  it("fails closed for malformed endpoints while preserving unknown valid relation codes", () => {
    expect(knowledgeEdgeRows()).toEqual([]);
    expect(knowledgeEdgeRows(null)).toEqual([]);
    expect(knowledgeEdgeRows({
      nodes: [
        undefined,
        { id: "", label: "No identifier" },
        { id: "no-label", label: "" },
        { id: "source", label: "Source", type: "" },
        { id: "target", label: "Target", type: "custom_entity" },
        { id: "unlabeled", type: "person" },
        { id: "space-source", label: "Space source", type: " " },
        { id: "space-target", label: "Space target", type: " " },
        { id: "empty-target", label: "Empty target", type: "" },
      ],
      edges: [
        undefined,
        { source: "", target: "target", relation: "custom_relation" },
        { source: "source", target: "target", relation: "custom_relation" },
        { source: "source", target: "unlabeled", relation: "custom_relation" },
        { source: "source", target: "target" },
        { source: "space-source", target: "space-target", relation: "custom_relation" },
        { source: "source", target: "empty-target", relation: "custom_relation" },
      ],
    })).toEqual([{
      evidenceLabel: "근거 상태 미상",
      relation: "custom_relation",
      relationLabel: "근거 기반 연결",
      sourceLabel: "Source",
      sourceType: "node",
      sourceTypeLabel: "node",
      targetLabel: "Target",
      targetType: "custom_entity",
      targetTypeLabel: "custom_entity",
    }, {
      evidenceLabel: "근거 상태 미상",
      relation: "custom_relation",
      relationLabel: "근거 기반 연결",
      sourceLabel: "Space source",
      sourceType: "node",
      sourceTypeLabel: "node",
      targetLabel: "Space target",
      targetType: "node",
      targetTypeLabel: "node",
    }, {
      evidenceLabel: "근거 상태 미상",
      relation: "custom_relation",
      relationLabel: "근거 기반 연결",
      sourceLabel: "Source",
      sourceType: "node",
      sourceTypeLabel: "node",
      targetLabel: "Empty target",
      targetType: "node",
      targetTypeLabel: "node",
    }]);
  });
});

describe("customerTreeRows", () => {
  it("keeps known parent-child relationships, orphans, and cycles finite", () => {
    const rows = customerTreeRows(
      [
        { account_name: "Parent" },
        { account_name: "Child", parent_name: "Parent" },
        { account_name: "Orphan", parent_name: "Missing" },
        { account_name: "Cycle A", parent_name: "Cycle B" },
        { account_name: "Cycle B", parent_name: "Cycle A" },
        { account_name: "" },
      ],
      [
        { parent: "Parent", child: "Child" },
        { parent: "Missing", child: "Child" },
        { parent: "Cycle A", child: "Cycle B" },
        { parent: "Cycle B", child: "Cycle A" },
        {},
      ],
    );

    expect(rows.map(({ account, depth }) => [account.account_name, depth])).toEqual([
      ["Parent", 0],
      ["Child", 1],
      ["Orphan", 0],
      ["Cycle A", 0],
      ["Cycle B", 1],
    ]);
  });
});

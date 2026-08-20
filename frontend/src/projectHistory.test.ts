import { describe, expect, it } from "vitest";

import {
  groupProjectEvidence,
  PROJECT_HISTORY_MESSAGE_KEYS,
  projectHistoryText,
} from "./projectHistory";


describe("project-history evidence grouping", () => {
  it("converges explicit and semantic project identity without duplicate cards", () => {
    const groups = groupProjectEvidence([
      {
        project_key: "P-100",
        project_name: "Northridge renewal",
        evidence: "source_post.source_project_code",
        confidence: null,
        ontology_iri: "https://w3id.org/lineageweave#Project",
        extraction_method: "source_field_hint",
        resolution_status: "hint_only",
        provenance: "source_post.source_project_code",
      },
      {
        project_key: "Ｐ－１００",
        project_name: "Northridge renewal",
        evidence: "The project was named in the body.",
        confidence: 0.91,
        ontology_iri: "https://w3id.org/lineageweave#Project",
        extraction_method: "contextual_orchestrator_semantic",
        resolution_status: "semantic_candidate",
        provenance: "post_project_mention.evidence_text",
      },
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0].projectKey).toBe("P-100");
    expect(groups[0].projectName).toBe("Northridge renewal");
    expect(groups[0].evidence).toHaveLength(2);
    expect(groups[0].evidence[0].extraction_method).toBe("source_field_hint");
  });
});


describe("project-history locale contract", () => {
  it.each(["ko", "zh", "ja", "vi"] as const)(
    "contains every Buyer message in %s",
    (locale) => {
      for (const key of PROJECT_HISTORY_MESSAGE_KEYS) {
        expect(projectHistoryText(locale, key), `${locale}:${key}`).not.toBe(
          projectHistoryText("en", key),
        );
      }
    },
  );

  it("formats event and actor counts", () => {
    expect(projectHistoryText("en", "summaryCounts", { events: 5, actors: 3 })).toBe(
      "5 events · 3 observed actors",
    );
    expect(projectHistoryText("ko", "summaryCounts", { events: 5, actors: 3 })).toBe(
      "이벤트 5건 · 관찰된 담당자 3명",
    );
  });
});

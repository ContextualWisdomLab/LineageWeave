import { describe, expect, it } from "vitest";

import {
  projectHistoryEventTypeLabel,
  projectHistoryKeys,
  projectHistoryMatchSourceLabel,
} from "./projectHistory";

describe("projectHistoryKeys", () => {
  it("deduplicates compatibility- and case-normalized identities", () => {
    expect(
      projectHistoryKeys(
        [
          { project_key: "Ｐ-100", project_name: "Project", evidence: "source", confidence: null, ontology_iri: "", extraction_method: "source_field_hint", resolution_status: "hint_only", provenance: "test" },
          { project_key: "p-100", project_name: "Project", evidence: "semantic", confidence: null, ontology_iri: "", extraction_method: "semantic", resolution_status: "resolved", provenance: "test" },
        ],
        null,
        null,
      ),
    ).toEqual(["Ｐ-100"]);
  });

  it("uses a source identity when project evidence is empty", () => {
    expect(projectHistoryKeys([], "  ", " P-200 ")).toEqual([" P-200 "]);
  });

  it("keeps a distinct explicit source identity beside semantic evidence", () => {
    expect(
      projectHistoryKeys(
        [
          {
            project_key: "semantic-project",
            project_name: "Semantic project",
            evidence: "semantic",
            confidence: null,
            ontology_iri: "",
            extraction_method: "semantic",
            resolution_status: "resolved",
            provenance: "test",
          },
        ],
        "SOURCE-200",
        "Source project",
      ),
    ).toEqual(["semantic-project", "SOURCE-200"]);
  });

  it("keeps storage fields and unknown event codes out of customer labels", () => {
    expect(projectHistoryMatchSourceLabel("en", "source_post.source_project_name")).toBe(
      "Source record",
    );
    expect(projectHistoryMatchSourceLabel("en", "post_project_mention.project_name")).toBe(
      "Supporting record",
    );
    expect(projectHistoryMatchSourceLabel("en", "future_table.future_column")).toBe(
      "Recorded evidence",
    );
    expect(projectHistoryEventTypeLabel("en", "future_event_code")).toBe("Source record");
  });
});

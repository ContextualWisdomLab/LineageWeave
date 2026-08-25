import { describe, expect, it } from "vitest";

import { projectHistoryKeys } from "./projectHistory";

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

  it("uses a source fallback only when project evidence is empty", () => {
    expect(projectHistoryKeys([], "  ", " P-200 ")).toEqual([" P-200 "]);
  });
});

import { describe, expect, it } from "vitest";

import type { OntologyNeighborhoodPayload } from "./api";
import { neighborhoodCsv } from "./ontologyLayout";

function csvWithSourceLabel(sourceLabel: string): string {
  const payload = {
    exact_value_rows: [
      {
        edge_id: "edge-1",
        source_label: sourceLabel,
        property_label: "relates to",
        target_label: "Target",
        truth_status_code: "truth_authoritative",
        recorded_at: "2026-09-05T00:00:00Z",
        ontology_property_iri: "https://example.test/ontology#relatesTo",
        property_code: "relatesTo",
        source_node_id: "source",
        target_node_id: "target",
      },
    ],
    voice_assignments: [],
  } as unknown as OntologyNeighborhoodPayload;
  return neighborhoodCsv(payload);
}

describe("ontology CSV spreadsheet safety", () => {
  it.each([
    ["\t=1+1", "'\t=1+1"],
    ["\r=1+1", "\"'\r=1+1\""],
    ["\n=1+1", "\"'\n=1+1\""],
    ["\u0000=1+1", "'\u0000=1+1"],
    ["＝1+1", "'＝1+1"],
    ["＋1+1", "'＋1+1"],
    ["－1+1", "'－1+1"],
    ["＠SUM(A1:A2)", "'＠SUM(A1:A2)"],
  ])("neutralizes formula-triggering source label %j", (sourceLabel, escapedCell) => {
    expect(csvWithSourceLabel(sourceLabel)).toContain(`edge-1,${escapedCell},relates to`);
  });
});

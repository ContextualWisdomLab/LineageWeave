import { describe, expect, it } from "vitest";
import { analysisRunCaption, shortDigest } from "./analysisRunDisplay";
import type { AnalysisRun } from "./api";

const sampleRun: AnalysisRun = {
  analysis_run_id: "run-demo-lineage",
  run_kind_code: "analysis_run_lineage",
  run_kind_label: "Lineage reconstruction",
  scope_kind_code: "analysis_scope_corporate_entity",
  scope_kind_label: "Corporate entity",
  scope_entity_name: "Demo Corp",
  status_code: "analysis_status_succeeded",
  status_label: "Succeeded",
  knowledge_cutoff: "2026-01-12T12:00:00Z",
  requested_at: "2026-01-12T12:30:00Z",
  source_counts: [],
};

describe("analysisRunCaption", () => {
  it("joins kind, status, and scope so the operator knows which run to open", () => {
    expect(analysisRunCaption(sampleRun)).toBe(
      "Lineage reconstruction · Succeeded · Demo Corp",
    );
  });
});

describe("shortDigest", () => {
  it("returns a 12-character prefix for comparing an approved revision", () => {
    expect(shortDigest("c".repeat(40))).toBe("c".repeat(12));
  });

  it("returns null when a digest is missing so the UI can hide the row", () => {
    expect(shortDigest(undefined)).toBeNull();
  });
});

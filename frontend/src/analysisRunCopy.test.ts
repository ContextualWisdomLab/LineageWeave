import { describe, expect, it } from "vitest";
import type { AnalysisRun } from "./api";
import {
  analysisRunCaption,
  analysisRunDocumentCountLabel,
  analysisRunNextAction,
} from "./analysisRunCopy";

function run(overrides: Partial<AnalysisRun>): AnalysisRun {
  return {
    analysis_run_id: "run-1",
    run_kind_code: "analysis_run_lineage",
    run_kind_label: "Lineage reconstruction",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    status_code: "analysis_status_pending",
    status_label: "Pending",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:01:00Z",
    source_counts: [
      {
        count_type_code: "analysis_count_document",
        count_type_label: "Documents",
        count_value: 3,
      },
    ],
    ...overrides,
  };
}

describe("analysisRunCopy", () => {
  it("keeps the home caption as kind · status · entity", () => {
    expect(analysisRunCaption(run({}))).toBe("Lineage reconstruction · Pending · Demo Corp");
  });

  it("tells a pending lineage buyer reconstruction has not started", () => {
    const copy = analysisRunNextAction(run({}));
    expect(copy).toMatch(/Reconstruction has not started yet/);
    expect(copy).not.toMatch(/measurement service/i);
    expect(copy).not.toMatch(/theta/i);
  });

  it("keeps a pending TEPP row from claiming a calibrated measurement", () => {
    const copy = analysisRunNextAction(
      run({
        run_kind_code: "analysis_run_tepp",
        run_kind_label: "TEPP measurement",
      }),
    );
    expect(copy).toMatch(/not a calibrated result/);
    expect(copy).not.toMatch(/reconstruction/i);
    expect(copy).not.toMatch(/theta/i);
  });

  it("sends a failed lineage row back to reconstruction, not TEPP", () => {
    const copy = analysisRunNextAction(
      run({
        status_code: "analysis_status_failed",
        status_label: "Failed",
      }),
    );
    expect(copy).toMatch(/retry reconstruction/);
    expect(copy).not.toMatch(/measurement service/);
  });

  it("sends a failed TEPP row to the measurement service", () => {
    const copy = analysisRunNextAction(
      run({
        run_kind_code: "analysis_run_tepp",
        run_kind_label: "TEPP measurement",
        status_code: "analysis_status_failed",
        status_label: "Failed",
      }),
    );
    expect(copy).toMatch(/measurement service/);
    expect(copy).not.toMatch(/reconstruction/i);
  });

  it("labels the cutoff document count for the home row", () => {
    expect(analysisRunDocumentCountLabel(run({}))).toBe("3 documents");
  });
});

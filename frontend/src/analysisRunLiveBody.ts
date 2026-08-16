/**
 * Compare a live post write clock with an analysis-run knowledge cutoff.
 *
 * Post-body versioning is later work (ADR 0016). Until a cutoff snapshot
 * exists, the operator must see whether today's row was written after
 * the analysis clock before treating the opened text as evidence.
 *
 * World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
 * Recommendation). https://www.w3.org/TR/owl-time/
 *
 * International Organization for Standardization. (2019).
 * *ISO 8601-1:2019: Date and time—Representations for information
 * interchange—Part 1: Basic rules*.
 */
export function analysisRunLiveBodyComparison(
  knowledgeCutoffIso: string,
  updatedAtIso: string,
): string {
  const cutoffDate = knowledgeCutoffIso.slice(0, 10);
  const writtenAfterCutoff = Date.parse(updatedAtIso) > Date.parse(knowledgeCutoffIso);
  if (writtenAfterCutoff) {
    return (
      `This live body was last written after cutoff ${cutoffDate}. ` +
      "Do not treat it as reconstructed evidence."
    );
  }
  return (
    `This live body has not been written since cutoff ${cutoffDate}. ` +
    "You can treat the opened text as the cutoff corpus for this run."
  );
}

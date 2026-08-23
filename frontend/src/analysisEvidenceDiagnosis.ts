/**
 * Reader diagnosis for missing-versus-negative analysis evidence (ADR 0135).
 *
 * Catalog-unbound, dropped/unavailable channel, and confident-negative are
 * three distinct states. A Null channel is not a zero score, and a source
 * phrase is not a catalog relationship.
 */

export type AnalysisEvidenceDiagnosisKind =
  | "catalog_unbound"
  | "dropped_channel"
  | "confident_negative";

export type AnalysisEvidenceDiagnosis = {
  kind: AnalysisEvidenceDiagnosisKind;
  title: string;
  nextAction: string;
};

export function analysisEvidenceDiagnosis(
  kind: AnalysisEvidenceDiagnosisKind,
): AnalysisEvidenceDiagnosis {
  switch (kind) {
    case "catalog_unbound":
      return {
        kind,
        title: "Not linked to a catalog row",
        nextAction:
          "Keep reading this mention as unbound, or open the catalog to bind it. This is not a missing analysis channel and not a negative extraction.",
      };
    case "dropped_channel":
      return {
        kind,
        title: "This analysis channel is unavailable",
        nextAction:
          "Continue with the remaining evidence, or retry when the channel is connected. A missing signal is not a negative fact.",
      };
    case "confident_negative":
      return {
        kind,
        title: "The source evidence is confidently negative",
        nextAction:
          "Read the source sentence, then continue. This is a measured negative, not an unavailable channel.",
      };
    default: {
      const unexpected: never = kind;
      throw new Error(`Unsupported analysis evidence diagnosis: ${String(unexpected)}`);
    }
  }
}

export function gluedRoleRelationshipNextAction(): string {
  return (
    "This R&R row is one source phrase. Do not treat it as a catalog " +
    "relationship until job title and relationship type are stored separately."
  );
}

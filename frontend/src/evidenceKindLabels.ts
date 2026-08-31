import { t } from "./i18n";

const CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = {
  source_field: "Source field hint",
  semantic_project: "Related project",
  semantic_role: "Related role",
  semantic_keyman: "Related key person",
  time_axis: "Time axis",
};

export function chatEvidenceKindLabel(kind: string): string {
  return t(CHAT_EVIDENCE_KIND_LABELS[kind] ?? "Evidence");
}

import { t } from "./i18n";

const CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = {
  source_field: "Source field hint",
  semantic_project: "Semantic project",
  semantic_role: "Semantic role",
  semantic_keyman: "Semantic Keyman",
};

export function chatEvidenceKindLabel(kind: string): string {
  return t(CHAT_EVIDENCE_KIND_LABELS[kind] ?? "Evidence");
}

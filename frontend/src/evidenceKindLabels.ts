import { t } from "./i18n";

const CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = {
  source_field: "Record detail",
  semantic_project: "Project",
  semantic_role: "Role",
  semantic_keyman: "Key contact",
  time_axis: "Time axis",
};

export function chatEvidenceKindLabel(kind: string): string {
  return t(CHAT_EVIDENCE_KIND_LABELS[kind] ?? "Evidence");
}

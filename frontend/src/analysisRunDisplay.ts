import type { AnalysisRun, AnalysisRunCount } from "./api";

/**
 * Buyer-facing caption for one authorized analysis run.
 *
 * Combines kind, latest status, and scope so the home list tells the
 * operator which reconstruction they are about to open.
 */
export function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Shorten a reproducibility digest for the home detail.
 *
 * Full SHA values stay on the API payload; the UI shows enough prefix
 * to compare against an approved revision without dumping a raw hash.
 */
export function shortDigest(value: string | undefined, length = 12): string | null {
  if (!value) return null;
  return value.slice(0, length);
}

/**
 * Label a frozen snapshot aggregate so it is not read as the cutoff list.
 *
 * ADR 0013 stores counts on the capture, not on the run. The home panel
 * must say they describe the snapshot, or "3 documents" looks like the
 * two in-cutoff Demo posts plus the late counter-example.
 */
export function snapshotCountCaption(count: AnalysisRunCount): string {
  return `${count.count_value} ${count.count_type_label.toLowerCase()} in the snapshot`;
}

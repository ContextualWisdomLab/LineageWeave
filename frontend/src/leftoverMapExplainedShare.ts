/** Leftover-map explained leftover share ``e = R̂² / R²`` of raw residual. */

export const LEFTOVER_MAP_EXPLAINED_SHARE_ACTION =
  "Leftover map leaves explained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL =
  "Leftover map comparison explained leftover share";

export function formatLeftoverMapExplainedShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `R\u0302\u00b2/R\u00b2 ${value.toFixed(2)}`;
}

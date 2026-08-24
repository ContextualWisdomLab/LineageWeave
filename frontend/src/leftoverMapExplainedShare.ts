/** Explained leftover share ``e = R̂_c² / R̃²`` of centered leftover. */

export const LEFTOVER_MAP_EXPLAINED_SHARE_ACTION =
  "Two leftover-map axes explain {value} of centered leftover after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverMapExplainedShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value) || value < 0) {
    return null;
  }
  return `R\u0302c\u00b2/R\u0303\u00b2 ${value.toFixed(2)}`;
}

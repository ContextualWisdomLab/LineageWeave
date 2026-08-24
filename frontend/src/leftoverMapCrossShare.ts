/** Leftover-map cross share ``x = 2 R̂_c U_c / R̃²`` of centered leftover. */

export const LEFTOVER_MAP_CROSS_SHARE_ACTION =
  "Two leftover-map axes leave identity remainder {value} of centered leftover after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverMapCrossShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `2R\u0302U/R\u0303\u00b2 ${value.toFixed(2)}`;
}

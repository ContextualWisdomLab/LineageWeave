/** Leftover-map cross share ``x = 2 R̂ U / R²`` of raw residual. */

export const LEFTOVER_MAP_CROSS_SHARE_ACTION =
  "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL =
  "Leftover map comparison cross share";

export function formatLeftoverMapCrossShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `2R\u0302U/R\u00b2 ${value.toFixed(2)}`;
}

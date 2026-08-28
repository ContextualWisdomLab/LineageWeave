/** Leftover-map unexplained leftover share ``s = U² / R²`` of raw residual. */

export const LEFTOVER_MAP_UNEXPLAINED_SHARE_ACTION =
  "Leftover map leaves unexplained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverMapUnexplainedShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `U\u00b2/R\u00b2 ${value.toFixed(2)}`;
}

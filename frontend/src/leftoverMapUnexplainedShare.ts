/** Unexplained leftover share ``s = U_c² / R̃²`` of centered leftover. */

export const LEFTOVER_MAP_UNEXPLAINED_SHARE_ACTION =
  "Leftover map leaves unexplained share {value} of centered leftover after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverMapUnexplainedShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value) || value < 0) {
    return null;
  }
  return `U\u00b2/R\u0303\u00b2 ${value.toFixed(2)}`;
}

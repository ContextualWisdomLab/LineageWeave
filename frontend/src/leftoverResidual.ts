/** Signed leftover residual ``R = Y − E[Y|θ, item]`` after IRT main effects. */

export const LEFTOVER_RESIDUAL_ACTION =
  "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverResidual(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }
  const magnitude = Math.abs(value).toFixed(2);
  if (value > 0) {
    return `+${magnitude}`;
  }
  if (value < 0) {
    return `\u2212${magnitude}`;
  }
  return magnitude;
}

/** Signed leftover residual ``R = Y − E[Y|θ, item]`` after IRT main effects. */
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

export function formatLeftoverMapResidual(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `R ${formatLeftoverResidual(value)}`;
}

export const LEFTOVER_MAP_COMPARE_RESIDUAL_LABEL =
  "Leftover map comparison residual";


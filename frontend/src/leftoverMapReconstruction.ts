/** Two-axis leftover-map reconstruction ``R̂ = ξ_{1:2} · ζ_{1:2}``. */

export const LEFTOVER_MAP_RECONSTRUCTION_ACTION =
  "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.";

export function formatSignedLeftoverValue(value: number): string | null {
  if (!Number.isFinite(value)) {
    return null;
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

export function formatLeftoverMapReconstruction(value: number | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  const signed = formatSignedLeftoverValue(value);
  return signed === null ? null : `R\u0302 ${signed}`;
}

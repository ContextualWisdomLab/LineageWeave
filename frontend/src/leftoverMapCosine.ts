/** Gabriel leftover-map cosine after IRT main effects. */

export const LEFTOVER_MAP_COSINE_ACTION =
  "Leftover-map cosine {value} names leftover-map alignment independent of distance. Open this post to read {criterion}.";

export function formatSignedLeftoverValue(value: number): string | null {
  if (!Number.isFinite(value)) {
    return null;
  }
  const magnitude = Math.abs(value).toFixed(2);
  if (value > 0) {
    return `+${magnitude}`;
  }
  if (value < 0) {
    return `−${magnitude}`;
  }
  return magnitude;
}

export function formatLeftoverMapCosine(value: number | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  const signed = formatSignedLeftoverValue(value);
  return signed === null ? null : `cos ${signed}`;
}

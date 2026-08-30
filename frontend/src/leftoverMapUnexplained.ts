/** Unexplained leftover ``U = R − R̂`` after two-axis reconstruction. */

export const LEFTOVER_MAP_UNEXPLAINED_ACTION =
  "Leftover map leaves unexplained U {value} after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_UNEXPLAINED_LABEL =
  "Leftover map comparison unexplained leftover";

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

export function formatLeftoverMapUnexplained(value: number | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  const signed = formatSignedLeftoverValue(value);
  return signed === null ? null : `U ${signed}`;
}

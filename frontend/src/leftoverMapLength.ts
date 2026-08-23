/** Gabriel leftover-map lengths ``‖ξ‖`` and ``‖ζ‖`` after IRT main effects. */

export const LEFTOVER_MAP_LENGTH_ACTION =
  "Leftover-map length ‖ξ‖ {person} and ‖ζ‖ {item} names leftover-map magnitude independently of leftover-map distance. Open this post to read {criterion}.";

export function formatLeftoverMapLength(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value) || value < 0) {
    return null;
  }
  return value.toFixed(2);
}

export function formatLeftoverMapPersonLength(value: number | null | undefined): string | null {
  const formatted = formatLeftoverMapLength(value);
  return formatted === null ? null : `‖ξ‖ ${formatted}`;
}

export function formatLeftoverMapItemLength(value: number | null | undefined): string | null {
  const formatted = formatLeftoverMapLength(value);
  return formatted === null ? null : `‖ζ‖ ${formatted}`;
}

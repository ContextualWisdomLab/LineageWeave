/** Gabriel leftover-map inner product ``ξ·ζ`` after IRT main effects. */

export const LEFTOVER_INNER_PRODUCT_ACTION =
  "Leftover-map inner product ξ·ζ {value} reconstructs leftover residual after IRT main effects. Open this post to read {criterion}.";

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

export function formatLeftoverInnerProduct(value: number | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  const signed = formatSignedLeftoverValue(value);
  return signed === null ? null : `ξ·ζ ${signed}`;
}

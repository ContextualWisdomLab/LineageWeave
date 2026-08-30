/** Observed Y and expected E[Y|θ, item] after IRT main effects. */

export function formatLeftoverObservedExpected(
  observed: number | null | undefined,
  expected: number | null | undefined,
): string | null {
  if (
    observed == null ||
    expected == null ||
    !Number.isFinite(observed) ||
    !Number.isFinite(expected)
  ) {
    return null;
  }
  return `Y ${observed.toFixed(2)} · E ${expected.toFixed(2)}`;
}

export function formatLeftoverMapObserved(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `Y ${value.toFixed(2)}`;
}

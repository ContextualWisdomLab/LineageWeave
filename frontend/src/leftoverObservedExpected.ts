/** Observed Y and expected E[Y|θ, item] after IRT main effects. */

export const LEFTOVER_MAP_COMPARE_OBSERVED_LABEL =
  "Leftover map comparison observed";

export const LEFTOVER_MAP_COMPARE_EXPECTED_LABEL =
  "Leftover map comparison expected";

export const LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED =
  "leftover map comparison graphic leftover observed {label}";

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

export function formatLeftoverMapExpected(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `E ${value.toFixed(2)}`;
}

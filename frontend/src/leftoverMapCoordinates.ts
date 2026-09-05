/** Two-axis leftover-map coordinates ``ξ_{1:2}`` and ``ζ_{1:2}``. */

import { formatSignedLeftoverValue } from "./leftoverMapUnexplained";

export const LEFTOVER_MAP_COORDINATES_ACTION =
  "Leftover map places this post at ξ {person} and the criterion at ζ {item} after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_COORDINATES_LABEL =
  "Leftover map comparison coordinates";

const PERSON_BADGE = "\u03BE";
const ITEM_BADGE = "\u03B6";

export function formatLeftoverMapCoordinatePair(
  axis1: number | null | undefined,
  axis2: number | null | undefined,
): string | null {
  if (axis1 == null || axis2 == null) {
    return null;
  }
  const first = formatSignedLeftoverValue(axis1);
  const second = formatSignedLeftoverValue(axis2);
  if (first === null || second === null) {
    return null;
  }
  return `(${first}, ${second})`;
}

export function formatLeftoverMapCoordinates(
  personAxis1: number | null | undefined,
  personAxis2: number | null | undefined,
  itemAxis1: number | null | undefined,
  itemAxis2: number | null | undefined,
): string | null {
  const person = formatLeftoverMapCoordinatePair(personAxis1, personAxis2);
  const item = formatLeftoverMapCoordinatePair(itemAxis1, itemAxis2);
  if (person === null || item === null) {
    return null;
  }
  return `${PERSON_BADGE} ${person} ${ITEM_BADGE} ${item}`;
}

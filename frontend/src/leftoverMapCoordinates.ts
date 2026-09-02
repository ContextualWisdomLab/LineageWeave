/** Two-axis leftover-map coordinates ``ξ_{1:2}`` and ``ζ_{1:2}``.
 *  ADR 0347 names leftover-map origin on leftover-map graphic leftover-map
 *  criterion leftover-map item coordinates as leftoverMapPlotCriterionBadge
 *  independently of leftover-map person coordinates. leftoverMapListCriterionBadge
 *  stays leftover-map pair leftover-map criterion leftover-map item coordinate keys.
 *  ADR 0348 names leftover-map origin on leftover-map graphic leftover-map
 *  post leftover-map person coordinates as leftoverMapPlotPostBadge independently of leftover-map
 *  criterion leftover-map item coordinates. leftoverMapListPostBadge stays leftover-map pair leftover-map
 *  post leftover-map person coordinate keys.
 *  ADR 0349 names leftover-map origin on leftover-map comparison graphic leftover-map
 *  post leftover-map person coordinates as leftoverMapComparePlotPostBadge independently of leftover-map
 *  graphic leftover-map post leftover-map origin leftover-map person coordinates. leftoverMapListPostBadge stays leftover-map pair leftover-map
 *  post leftover-map person coordinate keys.
 *  ADR 0350 names leftover-map origin on leftover-map comparison graphic leftover-map
 *  criterion leftover-map item coordinates as leftoverMapComparePlotCriterionBadge independently of leftover-map
 *  comparison graphic leftover-map post leftover-map origin leftover-map person coordinates. leftoverMapListCriterionBadge stays leftover-map pair leftover-map
 *  criterion leftover-map item coordinate keys.
 *  ADR 0351 names leftover-map origin on leftover-map pair leftover-map post leftover-map
 *  person coordinates as leftoverMapListPostBadge independently of leftover-map comparison graphic leftover-map post leftover-map
 *  origin leftover-map person coordinates. leftoverMapCompareListPostBadge stays leftover-map comparison leftover-pair leftover-map
 *  post leftover-map person coordinate keys.
 *  ADR 0352 names leftover-map origin on leftover-map pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapListCriterionBadge independently of leftover-map pair leftover-map post leftover-map
 *  origin leftover-map person coordinates. leftoverMapCompareListCriterionBadge stays leftover-map comparison leftover-pair leftover-map
 *  criterion leftover-map item coordinate keys.
 */

import { formatSignedLeftoverValue } from "./leftoverMapUnexplained";

export const LEFTOVER_MAP_COORDINATES_ACTION =
  "Leftover map places this post at ξ {person} and the criterion at ζ {item} after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_COORDINATES_LABEL =
  "Leftover map comparison coordinates";

export const LEFTOVER_MAP_LIST_POST_ACTION =
  "leftover pair leftover-map post {title} at ξ {person}";

export const LEFTOVER_MAP_LIST_POST_ACTION_ORIGIN =
  "leftover pair leftover-map post {title} at leftover-map origin ξ {person}";

export const LEFTOVER_MAP_LIST_CRITERION =
  "leftover pair leftover-map criterion {label} at ζ {item}";

export const LEFTOVER_MAP_LIST_CRITERION_ORIGIN =
  "leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}";

export const LEFTOVER_MAP_COMPARE_LIST_POST_ACTION =
  "leftover map comparison leftover pair leftover-map post {title} at ξ {person}";

export const LEFTOVER_MAP_COMPARE_LIST_CRITERION =
  "leftover map comparison leftover pair leftover-map criterion {label} at ζ {item}";

const PERSON_BADGE = "\u03BE";
const ITEM_BADGE = "\u03B6";

export type LeftoverMapListPostBadge = {
  key: string;
  values: { title: string; person: string };
};

export type LeftoverMapListCriterionBadge = {
  key: string;
  values: { label: string; item: string };
};

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

/** True when the formatted leftover-map coordinate pair is leftover-map origin
 *  `(formatSignedLeftoverValue(0), formatSignedLeftoverValue(0))`. Rank-0 unused
 *  axes still name leftover-map origin `(0.00, 0.00)`. Do not invent leftover-map
 *  origin from leftover-map axis share or leftover-map singular values.
 */
export function leftoverMapPlotCoordinatePairIsOrigin(pairLabel: string): boolean {
  const origin = formatLeftoverMapCoordinatePair(0, 0);
  return origin !== null && pairLabel === origin;
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

/** ADR 0339 leftover-map pair leftover-map post leftover-map person coordinates ξ.
 *  ADR 0348 names leftover-map origin on leftover-map graphic leftover-map post leftover-map
 *  person coordinates as leftoverMapPlotPostBadge, not this helper.
 *  ADR 0349 names leftover-map origin on leftover-map comparison graphic leftover-map post leftover-map
 *  person coordinates as leftoverMapComparePlotPostBadge, not this helper.
 *  ADR 0351 names leftover-map origin on leftover-map pair leftover-map post leftover-map
 *  person coordinates as leftoverMapListPostBadge independently of leftover-map comparison graphic leftover-map post leftover-map
 *  origin leftover-map person coordinates.
 *  ADR 0352 names leftover-map origin on leftover-map pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapListCriterionBadge, not this helper.
 */
export function leftoverMapListPostBadge(
  title: string,
  axis1: number | null | undefined,
  axis2: number | null | undefined,
): LeftoverMapListPostBadge | null {
  const person = formatLeftoverMapCoordinatePair(axis1, axis2);
  if (person === null) {
    return null;
  }
  const origin = leftoverMapPlotCoordinatePairIsOrigin(person);
  return {
    key: origin ? LEFTOVER_MAP_LIST_POST_ACTION_ORIGIN : LEFTOVER_MAP_LIST_POST_ACTION,
    values: { title, person },
  };
}

/** ADR 0340 leftover-map pair leftover-map criterion leftover-map item coordinates ζ.
 *  ADR 0347 names leftover-map origin on leftover-map graphic leftover-map criterion
 *  leftover-map item coordinates as leftoverMapPlotCriterionBadge, not this helper.
 *  ADR 0350 names leftover-map origin on leftover-map comparison graphic leftover-map criterion
 *  leftover-map item coordinates as leftoverMapComparePlotCriterionBadge, not this helper.
 *  ADR 0352 names leftover-map origin on leftover-map pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapListCriterionBadge independently of leftover-map pair leftover-map post leftover-map
 *  origin leftover-map person coordinates.
 */
export function leftoverMapListCriterionBadge(
  label: string,
  axis1: number | null | undefined,
  axis2: number | null | undefined,
): LeftoverMapListCriterionBadge | null {
  const item = formatLeftoverMapCoordinatePair(axis1, axis2);
  if (item === null) {
    return null;
  }
  const origin = leftoverMapPlotCoordinatePairIsOrigin(item);
  return {
    key: origin ? LEFTOVER_MAP_LIST_CRITERION_ORIGIN : LEFTOVER_MAP_LIST_CRITERION,
    values: { label, item },
  };
}

/** ADR 0341 leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates ξ.
 *  ADR 0351 names leftover-map origin on leftover-map pair leftover-map post leftover-map
 *  person coordinates as leftoverMapListPostBadge, not this helper.
 */
export function leftoverMapCompareListPostBadge(
  title: string,
  axis1: number | null | undefined,
  axis2: number | null | undefined,
): LeftoverMapListPostBadge | null {
  const person = formatLeftoverMapCoordinatePair(axis1, axis2);
  if (person === null) {
    return null;
  }
  return { key: LEFTOVER_MAP_COMPARE_LIST_POST_ACTION, values: { title, person } };
}

/** ADR 0342 leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates ζ.
 *  ADR 0350 names leftover-map origin on leftover-map comparison graphic leftover-map criterion
 *  leftover-map item coordinates as leftoverMapComparePlotCriterionBadge, not this helper.
 *  ADR 0352 names leftover-map origin on leftover-map pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapListCriterionBadge, not this helper.
 */
export function leftoverMapCompareListCriterionBadge(
  label: string,
  axis1: number | null | undefined,
  axis2: number | null | undefined,
): LeftoverMapListCriterionBadge | null {
  const item = formatLeftoverMapCoordinatePair(axis1, axis2);
  if (item === null) {
    return null;
  }
  return { key: LEFTOVER_MAP_COMPARE_LIST_CRITERION, values: { label, item } };
}

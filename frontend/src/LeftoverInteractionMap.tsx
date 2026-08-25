/* oxlint-disable react/only-export-components -- deterministic stateless projection helpers are tested directly */
import type { LeftoverMapItem, LeftoverMapPerson, LeftoverPair } from "./api";
import { t, tf } from "./i18n";

const MAP_WIDTH = 360;
const MAP_HEIGHT = 240;
const MAP_PAD = 36;

export type ProjectedLeftoverPoint = {
  id: string;
  label: string;
  x: number;
  y: number;
  kind: "person" | "item";
  pairKinds: ("closest" | "farthest")[];
};

function pairKindsFor(
  id: string,
  kind: "person" | "item",
  pairs: LeftoverPair[],
): ("closest" | "farthest")[] {
  const kinds = new Set<"closest" | "farthest">();
  for (const pair of pairs) {
    const match = kind === "person" ? pair.post_id === id : pair.criterion_code === id;
    if (!match) continue;
    if (pair.pair_kind === "closest" || pair.pair_kind === "farthest") {
      kinds.add(pair.pair_kind);
    }
  }
  return [...kinds];
}

export function leftoverPairForCriterion(
  pairs: LeftoverPair[],
  criterionCode: string,
): LeftoverPair | null {
  let closest: LeftoverPair | null = null;
  let farthest: LeftoverPair | null = null;
  for (const pair of pairs) {
    if (pair.criterion_code !== criterionCode) continue;
    if (pair.pair_kind === "closest" && closest === null) closest = pair;
    if (pair.pair_kind === "farthest" && farthest === null) farthest = pair;
  }
  return closest ?? farthest;
}

export function projectLeftoverMap(
  persons: LeftoverMapPerson[],
  items: LeftoverMapItem[],
  itemLabel: (criterionCode: string) => string,
  pairs: LeftoverPair[] = [],
  width = MAP_WIDTH,
  height = MAP_HEIGHT,
  pad = MAP_PAD,
): { persons: ProjectedLeftoverPoint[]; items: ProjectedLeftoverPoint[] } {
  const raw = [
    ...persons.map((person) => ({
      id: person.post_id,
      label: person.post_title,
      axisOne: person.axis_one,
      axisTwo: person.axis_two,
      kind: "person" as const,
    })),
    ...items.map((item) => ({
      id: item.criterion_code,
      label: itemLabel(item.criterion_code),
      axisOne: item.axis_one,
      axisTwo: item.axis_two,
      kind: "item" as const,
    })),
  ];
  const xs = raw.map((point) => point.axisOne);
  const ys = raw.map((point) => point.axisTwo);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const scale = Math.min(
    spanX === 0 ? Number.POSITIVE_INFINITY : (width - 2 * pad) / spanX,
    spanY === 0 ? Number.POSITIVE_INFINITY : (height - 2 * pad) / spanY,
  );
  const boundedScale = Number.isFinite(scale) ? scale : 0;
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const toSvg = (axisOne: number, axisTwo: number) => ({
    x: width / 2 + (axisOne - centerX) * boundedScale,
    y: height / 2 - (axisTwo - centerY) * boundedScale,
  });
  return {
    persons: raw
      .filter((point) => point.kind === "person")
      .map((point) => {
        const { x, y } = toSvg(point.axisOne, point.axisTwo);
        return {
          id: point.id,
          label: point.label,
          x,
          y,
          kind: "person" as const,
          pairKinds: pairKindsFor(point.id, "person", pairs),
        };
      }),
    items: raw
      .filter((point) => point.kind === "item")
      .map((point) => {
        const { x, y } = toSvg(point.axisOne, point.axisTwo);
        return {
          id: point.id,
          label: point.label,
          x,
          y,
          kind: "item" as const,
          pairKinds: pairKindsFor(point.id, "item", pairs),
        };
      }),
  };
}

function activateLeftoverMapNode(
  event: { key: string; preventDefault: () => void },
  postId: string,
  onSelectPost: (postId: string) => void,
) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelectPost(postId);
  }
}

export function LeftoverInteractionMap({
  persons,
  items,
  pairs,
  itemLabel,
  onSelectPost,
}: {
  persons: LeftoverMapPerson[];
  items: LeftoverMapItem[];
  pairs: LeftoverPair[];
  itemLabel: (criterionCode: string) => string;
  onSelectPost: (postId: string) => void;
}) {
  if (persons.length === 0 && items.length === 0) {
    return null;
  }
  const projected = projectLeftoverMap(persons, items, itemLabel, pairs);
  const personById = Object.fromEntries(projected.persons.map((point) => [point.id, point]));
  const itemById = Object.fromEntries(projected.items.map((point) => [point.id, point]));
  return (
    <figure className="leftover-interaction-map">
      <figcaption>{t("Leftover interaction map after main effects")}</figcaption>
      <svg
        viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        width="100%"
        height={MAP_HEIGHT}
        role="group"
        aria-label={t("Leftover interaction map")}
      >
        {pairs.map((pair) => {
          const person = personById[pair.post_id];
          const item = itemById[pair.criterion_code];
          if (!person || !item) return null;
          const kindClass =
            pair.pair_kind === "farthest" ? "leftover-map-farthest" : "leftover-map-closest";
          return (
            <line
              key={`${pair.pair_kind}:${pair.post_id}:${pair.criterion_code}`}
              className={`leftover-map-pair ${kindClass}`}
              x1={person.x}
              y1={person.y}
              x2={item.x}
              y2={item.y}
            >
              <title>
                {t(pair.pair_kind === "farthest" ? "Farthest leftover" : "Closest leftover")}:{" "}
                {person.label} · {item.label}
              </title>
            </line>
          );
        })}
        {projected.items.map((point) => {
          const pair = leftoverPairForCriterion(pairs, point.id);
          const pairClass = point.pairKinds.map((kind) => ` leftover-map-${kind}`).join("");
          if (pair) {
            return (
              <g
                key={`item:${point.id}`}
                className={`leftover-map-item${pairClass}`}
                transform={`translate(${point.x}, ${point.y})`}
                role="button"
                tabIndex={0}
                aria-label={tf("Open leftover map criterion: {label}", { label: point.label })}
                onClick={() => onSelectPost(pair.post_id)}
                onKeyDown={(event) => activateLeftoverMapNode(event, pair.post_id, onSelectPost)}
              >
                <rect x={-6} y={-6} width={12} height={12} transform="rotate(45)" />
                <title>
                  {tf("Open this leftover map criterion to read the leftover pair post: {label}", {
                    label: point.label,
                  })}
                </title>
              </g>
            );
          }
          return (
            <g
              key={`item:${point.id}`}
              className={`leftover-map-item${pairClass}`}
              transform={`translate(${point.x}, ${point.y})`}
            >
              <rect x={-6} y={-6} width={12} height={12} transform="rotate(45)" />
              <title>{tf("Criterion: {label}", { label: point.label })}</title>
            </g>
          );
        })}
        {projected.persons.map((point) => (
          <g
            key={`person:${point.id}`}
            className={`leftover-map-person${point.pairKinds.map((kind) => ` leftover-map-${kind}`).join("")}`}
            transform={`translate(${point.x}, ${point.y})`}
            role="button"
            tabIndex={0}
            aria-label={tf("Open leftover map post: {label}", { label: point.label })}
            onClick={() => onSelectPost(point.id)}
            onKeyDown={(event) => activateLeftoverMapNode(event, point.id, onSelectPost)}
          >
            <circle r={7} />
            <title>{tf("Open this post on the leftover map: {label}", { label: point.label })}</title>
          </g>
        ))}
      </svg>
      <ul className="leftover-map-key">
        {projected.persons.map((point) => (
          <li key={`person-key:${point.id}`}>
            <button type="button" onClick={() => onSelectPost(point.id)}>
              {tf("Open post: {label}", { label: point.label })}
            </button>
          </li>
        ))}
        {projected.items.map((point) => {
          const pair = leftoverPairForCriterion(pairs, point.id);
          return (
            <li key={`item-key:${point.id}`}>
              {pair ? (
                <button type="button" onClick={() => onSelectPost(pair.post_id)}>
                  {tf("Open this leftover map criterion to read the leftover pair post: {label}", {
                    label: point.label,
                  })}
                </button>
              ) : (
                tf("Criterion: {label}", { label: point.label })
              )}
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

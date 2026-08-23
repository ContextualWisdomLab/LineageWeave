import type { LeftoverMapItem, LeftoverMapPerson, LeftoverPair } from "./api";

const MAP_WIDTH = 360;
const MAP_HEIGHT = 240;
const MAP_PAD = 36;

export type ProjectedLeftoverPoint = {
  id: string;
  label: string;
  x: number;
  y: number;
  kind: "person" | "item";
  pairKind?: "closest" | "farthest";
};

function pairKindFor(
  id: string,
  kind: "person" | "item",
  pairs: LeftoverPair[],
): "closest" | "farthest" | undefined {
  for (const pair of pairs) {
    const match = kind === "person" ? pair.post_id === id : pair.criterion_code === id;
    if (!match) continue;
    if (pair.pair_kind === "closest" || pair.pair_kind === "farthest") {
      return pair.pair_kind;
    }
  }
  return undefined;
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
  const toSvg = (axisOne: number, axisTwo: number) => ({
    x: spanX === 0 ? width / 2 : pad + ((axisOne - minX) / spanX) * (width - 2 * pad),
    y: spanY === 0 ? height / 2 : pad + ((maxY - axisTwo) / spanY) * (height - 2 * pad),
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
          pairKind: pairKindFor(point.id, "person", pairs),
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
          pairKind: pairKindFor(point.id, "item", pairs),
        };
      }),
  };
}

function truncateLabel(label: string): string {
  return label.length > 22 ? `${label.slice(0, 21)}…` : label;
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
      <figcaption>Leftover interaction map after main effects</figcaption>
      <svg
        viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        width="100%"
        height={MAP_HEIGHT}
        role="img"
        aria-label="Leftover interaction map"
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
                {pair.pair_kind === "farthest" ? "Farthest leftover" : "Closest leftover"}:{" "}
                {person.label} · {item.label}
              </title>
            </line>
          );
        })}
        {projected.items.map((point) => (
          <g
            key={`item:${point.id}`}
            className={`leftover-map-item${point.pairKind ? ` leftover-map-${point.pairKind}` : ""}`}
            transform={`translate(${point.x}, ${point.y})`}
          >
            <rect x={-6} y={-6} width={12} height={12} transform="rotate(45)" />
            <text x={10} y={4}>
              {truncateLabel(point.label)}
            </text>
            <title>{`Criterion: ${point.label}`}</title>
          </g>
        ))}
        {projected.persons.map((point) => (
          <g
            key={`person:${point.id}`}
            className={`leftover-map-person${point.pairKind ? ` leftover-map-${point.pairKind}` : ""}`}
            transform={`translate(${point.x}, ${point.y})`}
            role="button"
            tabIndex={0}
            aria-label={`Open leftover map post: ${point.label}`}
            onClick={() => onSelectPost(point.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectPost(point.id);
              }
            }}
          >
            <circle r={7} />
            <text x={10} y={4}>
              {truncateLabel(point.label)}
            </text>
            <title>{`Open this post on the leftover map: ${point.label}`}</title>
          </g>
        ))}
      </svg>
    </figure>
  );
}

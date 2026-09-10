import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CustomerEntityTreeRow } from "./App";
import { buildCustomerEntityTree } from "./customerEntityTree";
import type { CustomerMasterEntity } from "./api";
import { setLocale } from "./i18n";

vi.mock("react-oidc-context", () => ({
  useAuth: () => ({
    isLoading: false,
    isAuthenticated: false,
    error: undefined,
    user: undefined,
    signinRedirect: vi.fn(),
    signoutRedirect: vi.fn(),
  }),
}));

beforeEach(() => {
  setLocale("en");
});

function entity(
  id: string,
  parent: string | null,
  name = id,
): CustomerMasterEntity {
  return {
    corporate_entity_id: id,
    entity_name: name,
    corporate_entity_code: id,
    entity_level_code: "L",
    entity_level_label: "Level",
    parent_entity_id: parent,
  };
}

function flattenIds(
  nodes: ReturnType<typeof buildCustomerEntityTree>,
): string[] {
  const out: string[] = [];
  const stack = [...nodes].reverse();
  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) {
      continue;
    }
    out.push(node.entity.corporate_entity_id);
    for (let index = node.children.length - 1; index >= 0; index -= 1) {
      stack.push(node.children[index]);
    }
  }
  return out;
}

describe("#906 cycle-safe customer forest", () => {
  it("emits every entity exactly once for a pure two-entity cycle", () => {
    const tree = buildCustomerEntityTree([
      entity("A", "B"),
      entity("B", "A"),
    ]);
    expect(flattenIds(tree).sort()).toEqual(["A", "B"]);
    expect(tree).toHaveLength(1);
    expect(tree[0].ancestryNote).toBe("cycle-broken");
  });

  it("emits a self-parent entity once instead of dropping it", () => {
    const tree = buildCustomerEntityTree([entity("S", "S")]);
    expect(flattenIds(tree)).toEqual(["S"]);
    expect(tree[0].ancestryNote).toBe("self-parent");
  });

  it("preserves missing-parent-as-root and ordinary order", () => {
    const tree = buildCustomerEntityTree([
      entity("child", "ghost"),
      entity("root", null),
      entity("kid", "root"),
    ]);
    expect(flattenIds(tree)).toEqual(["child", "root", "kid"]);
    expect(tree[0].ancestryNote).toBe("unlisted-parent");
    expect(tree[1].ancestryNote).toBeUndefined();
  });

  it("keeps a large ordinary hierarchy within the pure-builder latency guard", () => {
    const entities = Array.from({ length: 2_000 }, (_, index) =>
      entity(String(index), index === 0 ? null : String(index - 1)),
    );
    const startedAt = performance.now();
    const tree = buildCustomerEntityTree(entities);
    const elapsedMs = performance.now() - startedAt;

    expect(tree).toHaveLength(1);
    expect(flattenIds(tree)).toHaveLength(2_000);
    // This is a narrow algorithmic regression guard, not the product p95 SLO.
    // The previous repeated-ancestry walk took seconds at this size.
    expect(elapsedMs).toBeLessThan(250);
  });

  it("renders both cycle members with an explicit ancestry note", () => {
    const tree = buildCustomerEntityTree([
      entity("A", "B", "Alpha"),
      entity("B", "A", "Beta"),
    ]);
    render(
      <ul>
        {tree.map((node) => (
          <CustomerEntityTreeRow
            key={node.entity.corporate_entity_id}
            node={node}
            depth={0}
            expandedEntityId={null}
            relatedByEntity={{}}
            relatedLoading={null}
            onToggle={() => undefined}
            onOpenPost={() => undefined}
          />
        ))}
      </ul>,
    );
    expect(screen.getByText("Alpha")).toBeDefined();
    expect(screen.getByText("Beta")).toBeDefined();
    expect(
      screen.getByText("Shown as top level: listed parent forms a cycle."),
    ).toBeDefined();
  });
});

import type { CustomerMasterEntity } from "./api";

export interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  children: CustomerEntityTreeNode[];
  // Presentation-only ancestry flag. The entity DTO is never mutated:
  // a broken presentation edge still renders the entity exactly once.
  ancestryNote?: "cycle-broken" | "self-parent" | "unlisted-parent";
}

// Customer Master's visible entities form a forest, but ABAC can authorize
// a child without its parent and stored parents can cycle (or self-point),
// so the drawable forest must be derived defensively: every input entity is
// emitted exactly once, ordinary order is preserved, and only the
// presentation edge needed to establish a root is broken (#906).
export function buildCustomerEntityTree(entities: CustomerMasterEntity[]): CustomerEntityTreeNode[] {
  const byId = new Map(entities.map((entity) => [entity.corporate_entity_id, entity]));
  // Tentative presentation parents: visible and non-self only.
  const parentOf = new Map<string, string | null>();
  const noteOf = new Map<string, NonNullable<CustomerEntityTreeNode["ancestryNote"]>>();
  for (const entity of entities) {
    const id = entity.corporate_entity_id;
    const parent = entity.parent_entity_id;
    if (!parent || !byId.has(parent)) {
      parentOf.set(id, null);
      if (parent) {
        noteOf.set(id, "unlisted-parent");
      }
    } else if (parent === id) {
      parentOf.set(id, null);
      noteOf.set(id, "self-parent");
    } else {
      parentOf.set(id, parent);
    }
  }

  // Each entity joins at most one parent, so the visible hierarchy is a
  // functional graph. Settle each path once: if the current path revisits
  // one of its own members, cut only the edge that closes that cycle. The
  // first input-order traversal therefore keeps the same deterministic
  // presentation rule without repeatedly walking already-settled ancestry.
  const settled = new Set<string>();
  for (const entity of entities) {
    const start = entity.corporate_entity_id;
    if (settled.has(start)) {
      continue;
    }
    const path: string[] = [];
    const pathIndex = new Map<string, number>();
    let cursor: string | null = start;
    while (cursor !== null && !settled.has(cursor) && !pathIndex.has(cursor)) {
      pathIndex.set(cursor, path.length);
      path.push(cursor);
      cursor = parentOf.get(cursor) ?? null;
    }
    if (cursor !== null && pathIndex.has(cursor)) {
      const predecessor = path[path.length - 1];
      parentOf.set(predecessor, null);
      noteOf.set(predecessor, "cycle-broken");
    }
    for (const id of path) {
      settled.add(id);
    }
  }

  // Materialize iteratively instead of recursively rebuilding every subtree.
  // This keeps a malformed but very deep visible hierarchy from consuming the
  // JavaScript call stack while preserving input order for roots and siblings.
  const nodeById = new Map<string, CustomerEntityTreeNode>();
  for (const entity of entities) {
    const id = entity.corporate_entity_id;
    nodeById.set(id, {
      entity,
      children: [],
      ...(noteOf.has(id) ? { ancestryNote: noteOf.get(id) } : {}),
    });
  }

  const roots: CustomerEntityTreeNode[] = [];
  for (const entity of entities) {
    const id = entity.corporate_entity_id;
    const node = nodeById.get(id);
    if (!node) {
      continue;
    }
    const parent = parentOf.get(id);
    if (parent) {
      nodeById.get(parent)?.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

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
  // Break presentation cycles deterministically: walking from each entity
  // in input order, the edge closing a revisited ancestor is cut so its
  // predecessor becomes a root. Earlier members keep their edges, so the
  // result is stable for a given input order and always acyclic.
  for (const entity of entities) {
    const path: string[] = [];
    let cursor: string | null = entity.corporate_entity_id;
    while (cursor !== null && !path.includes(cursor)) {
      path.push(cursor);
      cursor = parentOf.get(cursor) ?? null;
    }
    if (cursor !== null) {
      const predecessor = path[path.length - 1];
      parentOf.set(predecessor, null);
      noteOf.set(predecessor, "cycle-broken");
    }
  }
  const childrenByParent = new Map<string, CustomerMasterEntity[]>();
  const roots: CustomerMasterEntity[] = [];
  for (const entity of entities) {
    const parent = parentOf.get(entity.corporate_entity_id);
    if (parent) {
      const siblings = childrenByParent.get(parent) ?? [];
      siblings.push(entity);
      childrenByParent.set(parent, siblings);
    } else {
      roots.push(entity);
    }
  }
  const toNode = (entity: CustomerMasterEntity): CustomerEntityTreeNode => ({
    entity,
    children: (childrenByParent.get(entity.corporate_entity_id) ?? []).map(toNode),
    ...(noteOf.has(entity.corporate_entity_id)
      ? { ancestryNote: noteOf.get(entity.corporate_entity_id) }
      : {}),
  });
  return roots.map(toNode);
}

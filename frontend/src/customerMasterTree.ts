import type { CustomerMasterEntity } from "./api";

/** A malformed source relation that cannot safely participate in the visible hierarchy. */
export type CustomerHierarchyIssue = "missing_parent" | "self_parent" | "cycle";

/** A cycle-safe customer master node projected from the authorized flat API response. */
export interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  children: CustomerEntityTreeNode[];
  hierarchyIssue: CustomerHierarchyIssue | null;
}

/** Metadata for one tree item in keyboard-navigation order. */
export interface VisibleCustomerTreeItem {
  node: CustomerEntityTreeNode;
  entityId: string;
  level: number;
  parentEntityId: string | null;
  positionInSet: number;
  setSize: number;
}

/**
 * Build an ordered forest without dropping authorized entities when a parent is missing or cyclic.
 *
 * Valid parent links are preserved. A missing parent, self-parent, or every member of a detected
 * cycle is promoted to a root and marked for buyer-visible review instead of disappearing.
 */
export function buildCustomerEntityForest(
  entities: readonly CustomerMasterEntity[],
): CustomerEntityTreeNode[] {
  const orderedEntities: CustomerMasterEntity[] = [];
  const byId = new Map<string, CustomerMasterEntity>();
  for (const entity of entities) {
    if (byId.has(entity.corporate_entity_id)) {
      continue;
    }
    byId.set(entity.corporate_entity_id, entity);
    orderedEntities.push(entity);
  }

  const parentById = new Map<string, string | null>();
  const issueById = new Map<string, CustomerHierarchyIssue>();
  for (const entity of orderedEntities) {
    const entityId = entity.corporate_entity_id;
    const parentId = entity.parent_entity_id;
    if (!parentId) {
      parentById.set(entityId, null);
    } else if (parentId === entityId) {
      parentById.set(entityId, null);
      issueById.set(entityId, "self_parent");
    } else if (!byId.has(parentId)) {
      parentById.set(entityId, null);
      issueById.set(entityId, "missing_parent");
    } else {
      parentById.set(entityId, parentId);
    }
  }

  const completed = new Set<string>();
  for (const startId of byId.keys()) {
    if (completed.has(startId)) continue;
    const path: string[] = [];
    const pathIndex = new Map<string, number>();
    let currentId: string | null = startId;
    while (currentId !== null && !completed.has(currentId)) {
      const repeatedAt = pathIndex.get(currentId);
      if (repeatedAt !== undefined) {
        for (const cycleId of path.slice(repeatedAt)) {
          parentById.set(cycleId, null);
          issueById.set(cycleId, "cycle");
        }
        break;
      }
      pathIndex.set(currentId, path.length);
      path.push(currentId);
      currentId = parentById.get(currentId) ?? null;
    }
    for (const entityId of path) completed.add(entityId);
  }

  const nodeById = new Map<string, CustomerEntityTreeNode>();
  for (const entity of orderedEntities) {
    nodeById.set(entity.corporate_entity_id, {
      entity,
      children: [],
      hierarchyIssue: issueById.get(entity.corporate_entity_id) ?? null,
    });
  }

  const roots: CustomerEntityTreeNode[] = [];
  for (const entity of orderedEntities) {
    const node = nodeById.get(entity.corporate_entity_id)!;
    const parentId = parentById.get(entity.corporate_entity_id) ?? null;
    if (parentId) {
      nodeById.get(parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

/** Return visible nodes in WAI-ARIA tree keyboard order for the current expansion state. */
export function flattenVisibleCustomerTree(
  roots: readonly CustomerEntityTreeNode[],
  expandedEntityIds: ReadonlySet<string>,
): VisibleCustomerTreeItem[] {
  const visible: VisibleCustomerTreeItem[] = [];
  const stack: VisibleCustomerTreeItem[] = [];
  for (let index = roots.length - 1; index >= 0; index -= 1) {
    const node = roots[index];
    stack.push({
      node,
      entityId: node.entity.corporate_entity_id,
      level: 1,
      parentEntityId: null,
      positionInSet: index + 1,
      setSize: roots.length,
    });
  }
  while (stack.length > 0) {
    const item = stack.pop()!;
    visible.push(item);
    if (!expandedEntityIds.has(item.entityId)) continue;
    const children = item.node.children;
    for (let index = children.length - 1; index >= 0; index -= 1) {
      const child = children[index];
      stack.push({
        node: child,
        entityId: child.entity.corporate_entity_id,
        level: item.level + 1,
        parentEntityId: item.entityId,
        positionInSet: index + 1,
        setSize: children.length,
      });
    }
  }
  return visible;
}

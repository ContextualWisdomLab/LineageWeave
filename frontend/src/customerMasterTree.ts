import type { CustomerMasterEntity } from "./api";

export type CustomerHierarchyIssue =
  | "cycle_parent_ignored"
  | "self_parent_ignored"
  | "parent_not_available";

export interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  hierarchyIssue: CustomerHierarchyIssue | null;
  children: CustomerEntityTreeNode[];
}

function compareEntity(left: CustomerMasterEntity, right: CustomerMasterEntity): number {
  if (left.entity_name < right.entity_name) return -1;
  if (left.entity_name > right.entity_name) return 1;
  if (left.corporate_entity_id < right.corporate_entity_id) return -1;
  if (left.corporate_entity_id > right.corporate_entity_id) return 1;
  return 0;
}

/**
 * Builds the authorized Customer Master hierarchy without hiding malformed records.
 *
 * Parent pointers are presentation evidence, not permission to discard an otherwise
 * authorized entity. Missing parents, self-parent edges, and one deterministic edge
 * per pure cycle are therefore omitted from the rendered forest and disclosed on the
 * promoted root. No replacement parent or organization is invented. Ordering uses
 * code-point comparison rather than runtime locale so repeated renders are stable.
 */
export function buildCustomerEntityTree(
  entities: CustomerMasterEntity[],
): CustomerEntityTreeNode[] {
  const byId = new Map(entities.map((entity) => [entity.corporate_entity_id, entity]));
  const parentById = new Map<string, string | null>();
  const issueById = new Map<string, CustomerHierarchyIssue>();

  for (const entity of entities) {
    const parentId = entity.parent_entity_id;
    if (!parentId) {
      parentById.set(entity.corporate_entity_id, null);
    } else if (parentId === entity.corporate_entity_id) {
      parentById.set(entity.corporate_entity_id, null);
      issueById.set(entity.corporate_entity_id, "self_parent_ignored");
    } else if (!byId.has(parentId)) {
      parentById.set(entity.corporate_entity_id, null);
      issueById.set(entity.corporate_entity_id, "parent_not_available");
    } else {
      parentById.set(entity.corporate_entity_id, parentId);
    }
  }

  const fullyVisited = new Set<string>();
  const orderedEntities = [...entities].sort(compareEntity);
  for (const startingEntity of orderedEntities) {
    if (fullyVisited.has(startingEntity.corporate_entity_id)) continue;

    const path: string[] = [];
    const pathIndex = new Map<string, number>();
    let currentId: string | null = startingEntity.corporate_entity_id;

    while (currentId && !fullyVisited.has(currentId)) {
      const repeatedAt = pathIndex.get(currentId);
      if (repeatedAt !== undefined) {
        const cycleIds = path.slice(repeatedAt);
        const breakEntity = cycleIds
          .map((id) => byId.get(id))
          .filter((entity): entity is CustomerMasterEntity => entity !== undefined)
          .sort(compareEntity)[0];
        if (breakEntity) {
          parentById.set(breakEntity.corporate_entity_id, null);
          issueById.set(breakEntity.corporate_entity_id, "cycle_parent_ignored");
        }
        break;
      }
      pathIndex.set(currentId, path.length);
      path.push(currentId);
      currentId = parentById.get(currentId) ?? null;
    }

    for (const id of path) fullyVisited.add(id);
  }

  const childrenByParent = new Map<string, CustomerMasterEntity[]>();
  const roots: CustomerMasterEntity[] = [];
  for (const entity of entities) {
    const parentId = parentById.get(entity.corporate_entity_id) ?? null;
    if (!parentId) {
      roots.push(entity);
      continue;
    }
    const children = childrenByParent.get(parentId) ?? [];
    children.push(entity);
    childrenByParent.set(parentId, children);
  }

  const toNode = (entity: CustomerMasterEntity): CustomerEntityTreeNode => ({
    entity,
    hierarchyIssue: issueById.get(entity.corporate_entity_id) ?? null,
    children: [...(childrenByParent.get(entity.corporate_entity_id) ?? [])]
      .sort(compareEntity)
      .map(toNode),
  });

  return roots.sort(compareEntity).map(toNode);
}

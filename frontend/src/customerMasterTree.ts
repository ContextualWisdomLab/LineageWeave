import type { CustomerMasterEntity } from "./apiTransport";

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
 * Indexes one authorized entity row per canonical corporate entity identity.
 *
 * A missing/blank or whitespace-aliased canonical identity cannot safely participate in
 * hierarchy joins, and a duplicated identity makes parent and child references ambiguous.
 * Rendering any of those cases would convert malformed transport data or response ordering
 * into business truth. The Customer Master therefore fails closed so the existing request
 * error state can disclose a data-integrity failure instead of rendering fabricated authority.
 * Opaque identities are rejected rather than silently trimmed or otherwise normalized.
 */
function indexEntitiesById(entities: CustomerMasterEntity[]): Map<string, CustomerMasterEntity> {
  const byId = new Map<string, CustomerMasterEntity>();
  for (const entity of entities) {
    if (
      typeof entity.corporate_entity_id !== "string" ||
      entity.corporate_entity_id.trim().length === 0
    ) {
      throw new Error("corporate_entity_id must be a non-blank string");
    }
    if (entity.corporate_entity_id.trim() !== entity.corporate_entity_id) {
      throw new Error("corporate_entity_id must not contain surrounding whitespace");
    }
    if (byId.has(entity.corporate_entity_id)) {
      throw new Error(`duplicate corporate_entity_id: ${entity.corporate_entity_id}`);
    }
    byId.set(entity.corporate_entity_id, entity);
  }
  return byId;
}

/**
 * Builds the authorized Customer Master hierarchy without hiding malformed records.
 *
 * Parent pointers are presentation evidence, not permission to discard an otherwise
 * authorized entity. Missing parents, self-parent edges, and one deterministic edge
 * per pure cycle are therefore omitted from the rendered forest and disclosed on the
 * promoted root. Missing/blank, whitespace-aliased, or conflicting duplicate canonical
 * entity identities fail closed because there is no safe presentation-only rule for
 * inventing, normalizing, or choosing source identity. No replacement parent or organization
 * is invented. Ordering uses code-point comparison rather than runtime locale so repeated
 * renders are stable. Node materialization is iterative so a valid, unusually deep hierarchy
 * cannot exhaust the JavaScript call stack.
 */
export function buildCustomerEntityTree(
  entities: CustomerMasterEntity[],
): CustomerEntityTreeNode[] {
  const byId = indexEntitiesById(entities);
  const parentById = new Map<string, string | null>();
  const issueById = new Map<string, CustomerHierarchyIssue>();

  for (const entity of entities) {
    const parentId = entity.parent_entity_id;
    if (parentId === null) {
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

  const nodeById = new Map<string, CustomerEntityTreeNode>();
  for (const entity of entities) {
    nodeById.set(entity.corporate_entity_id, {
      entity,
      hierarchyIssue: issueById.get(entity.corporate_entity_id) ?? null,
      children: [],
    });
  }

  const roots: CustomerEntityTreeNode[] = [];
  for (const entity of entities) {
    const node = nodeById.get(entity.corporate_entity_id)!;
    const parentId = parentById.get(entity.corporate_entity_id) ?? null;
    if (!parentId) {
      roots.push(node);
      continue;
    }
    nodeById.get(parentId)!.children.push(node);
  }

  for (const node of nodeById.values()) {
    node.children.sort((left, right) => compareEntity(left.entity, right.entity));
  }

  return roots.sort((left, right) => compareEntity(left.entity, right.entity));
}

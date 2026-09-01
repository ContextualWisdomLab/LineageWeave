import type { CustomerMasterEntity } from "./api";

export type CustomerHierarchyIssue =
  | "cycle_parent_ignored"
  | "self_parent_ignored"
  | "parent_not_available";

export interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  children: CustomerEntityTreeNode[];
  hierarchy_issue?: CustomerHierarchyIssue;
  source_parent_entity_id?: string;
}

function compareEntity(left: CustomerMasterEntity, right: CustomerMasterEntity): number {
  if (left.entity_name < right.entity_name) return -1;
  if (left.entity_name > right.entity_name) return 1;
  if (left.corporate_entity_id < right.corporate_entity_id) return -1;
  if (left.corporate_entity_id > right.corporate_entity_id) return 1;
  return 0;
}

/**
 * Builds the Customer Master presentation forest without changing catalog truth.
 *
 * The API may legitimately omit an unauthorized parent, and malformed imported
 * catalogs can contain self-parent pointers or a closed parent cycle. Those
 * parent references remain on the source entity, while this presentation model
 * omits only the unsafe/unavailable edge and records why. The break point for a
 * longer cycle and all sibling/root ordering use raw code-point ordering so the
 * same authorized payload renders identically across locales and serializers.
 */
export function buildCustomerEntityTree(
  entities: CustomerMasterEntity[],
): CustomerEntityTreeNode[] {
  const byId = new Map(entities.map((entity) => [entity.corporate_entity_id, entity]));
  const effectiveParent = new Map<string, string | null>();
  const issues = new Map<string, CustomerHierarchyIssue>();

  for (const entity of entities) {
    const parentId = entity.parent_entity_id;
    if (!parentId) {
      effectiveParent.set(entity.corporate_entity_id, null);
    } else if (parentId === entity.corporate_entity_id) {
      effectiveParent.set(entity.corporate_entity_id, null);
      issues.set(entity.corporate_entity_id, "self_parent_ignored");
    } else if (!byId.has(parentId)) {
      effectiveParent.set(entity.corporate_entity_id, null);
      issues.set(entity.corporate_entity_id, "parent_not_available");
    } else {
      effectiveParent.set(entity.corporate_entity_id, parentId);
    }
  }

  const inspected = new Set<string>();
  for (const origin of entities) {
    if (inspected.has(origin.corporate_entity_id)) continue;

    const path: string[] = [];
    const pathIndex = new Map<string, number>();
    let currentId: string | null = origin.corporate_entity_id;

    while (currentId && !inspected.has(currentId)) {
      const existingIndex = pathIndex.get(currentId);
      if (existingIndex !== undefined) {
        const cycleIds = path.slice(existingIndex);
        const breakEntity = cycleIds
          .map((entityId) => byId.get(entityId))
          .filter((entity): entity is CustomerMasterEntity => entity !== undefined)
          .sort(compareEntity)[0];
        if (breakEntity) {
          effectiveParent.set(breakEntity.corporate_entity_id, null);
          issues.set(breakEntity.corporate_entity_id, "cycle_parent_ignored");
        }
        break;
      }

      pathIndex.set(currentId, path.length);
      path.push(currentId);
      currentId = effectiveParent.get(currentId) ?? null;
    }

    path.forEach((entityId) => inspected.add(entityId));
  }

  const roots: CustomerMasterEntity[] = [];
  const childrenByParent = new Map<string, CustomerMasterEntity[]>();
  for (const entity of entities) {
    const parentId = effectiveParent.get(entity.corporate_entity_id) ?? null;
    if (!parentId) {
      roots.push(entity);
      continue;
    }
    const children = childrenByParent.get(parentId) ?? [];
    children.push(entity);
    childrenByParent.set(parentId, children);
  }

  const toNode = (entity: CustomerMasterEntity): CustomerEntityTreeNode => {
    const issue = issues.get(entity.corporate_entity_id);
    return {
      entity,
      children: (childrenByParent.get(entity.corporate_entity_id) ?? [])
        .slice()
        .sort(compareEntity)
        .map(toNode),
      ...(issue ? { hierarchy_issue: issue } : {}),
      ...(issue && entity.parent_entity_id
        ? { source_parent_entity_id: entity.parent_entity_id }
        : {}),
    };
  };

  return roots.slice().sort(compareEntity).map(toNode);
}

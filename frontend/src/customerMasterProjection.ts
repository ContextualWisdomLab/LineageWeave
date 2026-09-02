import type { CustomerMasterEntity, CustomerMasterResponse } from "./apiTransport";
import {
  buildCustomerEntityTree,
  type CustomerEntityTreeNode,
  type CustomerHierarchyIssue,
} from "./customerMasterTree";

const HIERARCHY_ISSUE_DISPLAY: Record<CustomerHierarchyIssue, string> = {
  cycle_parent_ignored: "Cyclic parent link omitted",
  self_parent_ignored: "Self-parent link omitted",
  parent_not_available: "Parent not available in this authorized view",
};

function flattenDisplayTree(
  nodes: CustomerEntityTreeNode[],
  parentEntityId: string | null,
  output: CustomerMasterEntity[],
): void {
  const pending = [...nodes]
    .reverse()
    .map((node) => ({ node, parentEntityId }));

  while (pending.length > 0) {
    const current = pending.pop()!;
    const suffix = current.node.hierarchyIssue
      ? ` · ${HIERARCHY_ISSUE_DISPLAY[current.node.hierarchyIssue]}`
      : "";
    output.push({
      ...current.node.entity,
      parent_entity_id: current.parentEntityId,
      entity_level_label: `${current.node.entity.entity_level_label}${suffix}`,
    });

    for (let index = current.node.children.length - 1; index >= 0; index -= 1) {
      pending.push({
        node: current.node.children[index],
        parentEntityId: current.node.entity.corporate_entity_id,
      });
    }
  }
}

/**
 * Produces the Customer Master display projection consumed by the existing tree UI.
 *
 * The API response remains immutable. Only the frontend projection rewrites malformed
 * parent pointers to the deterministic visible forest and composes disclosure into the
 * existing display label. `entity_level_code` and every other authoritative source fact
 * are preserved exactly; no corrected parent is invented or persisted. Traversal is
 * iterative so a valid deep hierarchy cannot fail solely because of JavaScript call-stack
 * depth.
 */
export function projectCustomerMasterResponse(
  response: CustomerMasterResponse,
): CustomerMasterResponse {
  const corporateEntities: CustomerMasterEntity[] = [];
  flattenDisplayTree(buildCustomerEntityTree(response.corporate_entities), null, corporateEntities);
  return { ...response, corporate_entities: corporateEntities };
}

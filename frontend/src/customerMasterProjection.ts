import type { CustomerMasterEntity, CustomerMasterResponse } from "./apiTransport";
import {
  buildCustomerEntityTree,
  type CustomerEntityTreeNode,
} from "./customerMasterTree";

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
    output.push({
      ...current.node.entity,
      parent_entity_id: current.parentEntityId,
      hierarchy_issue_code: current.node.hierarchyIssue,
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
 * parent pointers to the deterministic visible forest and carries a presentation-only issue
 * code for localized rendering. `entity_level_code` and every authoritative source fact
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

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
  for (const node of nodes) {
    const suffix = node.hierarchyIssue ? ` · ${HIERARCHY_ISSUE_DISPLAY[node.hierarchyIssue]}` : "";
    output.push({
      ...node.entity,
      parent_entity_id: parentEntityId,
      entity_level_label: `${node.entity.entity_level_label}${suffix}`,
    });
    flattenDisplayTree(node.children, node.entity.corporate_entity_id, output);
  }
}

/**
 * Produces the Customer Master display projection consumed by the existing tree UI.
 *
 * The API response remains immutable. Only the frontend projection rewrites malformed
 * parent pointers to the deterministic visible forest and composes disclosure into the
 * existing display label. `entity_level_code` and every other authoritative source fact
 * are preserved exactly; no corrected parent is invented or persisted.
 */
export function projectCustomerMasterResponse(
  response: CustomerMasterResponse,
): CustomerMasterResponse {
  const corporateEntities: CustomerMasterEntity[] = [];
  flattenDisplayTree(buildCustomerEntityTree(response.corporate_entities), null, corporateEntities);
  return { ...response, corporate_entities: corporateEntities };
}

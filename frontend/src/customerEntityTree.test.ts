import { describe, expect, it } from "vitest";
import type { CustomerMasterEntity } from "./api";
import {
  buildCustomerEntityTree,
  customerHierarchyIssueMessage,
} from "./customerEntityTree";

function entity(
  id: string,
  name: string,
  parentEntityId: string | null,
): CustomerMasterEntity {
  return {
    corporate_entity_id: id,
    corporate_entity_code: id.toUpperCase(),
    entity_name: name,
    entity_level_code: "entity_level_company",
    entity_level_label: "Company",
    parent_entity_id: parentEntityId,
  };
}

describe("buildCustomerEntityTree", () => {
  it("keeps a pure parent cycle visible by omitting one deterministic unsafe edge", () => {
    const result = buildCustomerEntityTree([
      entity("corp-b", "Beta", "corp-a"),
      entity("corp-a", "Alpha", "corp-b"),
    ]);

    expect(result).toHaveLength(1);
    expect(result[0].entity.corporate_entity_id).toBe("corp-a");
    expect(result[0].hierarchy_issue).toBe("cycle_parent_ignored");
    expect(result[0].source_parent_entity_id).toBe("corp-b");
    expect(result[0].children.map((child) => child.entity.corporate_entity_id)).toEqual([
      "corp-b",
    ]);
  });

  it("keeps self-parent and invisible-parent entities visible without inventing parents", () => {
    const result = buildCustomerEntityTree([
      entity("corp-self", "Self Co", "corp-self"),
      entity("corp-hidden-child", "Visible Child", "corp-hidden-parent"),
    ]);

    expect(result.map((node) => node.entity.corporate_entity_id)).toEqual([
      "corp-self",
      "corp-hidden-child",
    ]);
    expect(result[0]).toMatchObject({
      hierarchy_issue: "self_parent_ignored",
      source_parent_entity_id: "corp-self",
      children: [],
    });
    expect(result[1]).toMatchObject({
      hierarchy_issue: "parent_not_available",
      source_parent_entity_id: "corp-hidden-parent",
      children: [],
    });
  });

  it("produces the same forest for equivalent input in another serialization order", () => {
    const rows = [
      entity("corp-root", "Root", null),
      entity("corp-z", "Zulu", "corp-root"),
      entity("corp-a", "Alpha", "corp-root"),
    ];

    expect(buildCustomerEntityTree(rows.slice().reverse())).toEqual(buildCustomerEntityTree(rows));
    expect(
      buildCustomerEntityTree(rows)[0].children.map((child) => child.entity.corporate_entity_id),
    ).toEqual(["corp-a", "corp-z"]);
  });
});

describe("customerHierarchyIssueMessage", () => {
  it("does not disclose the unavailable parent identifier", () => {
    const message = customerHierarchyIssueMessage("parent_not_available");

    expect(message).toBe(
      "The parent is not available in this authorized view. This entity remains visible at the top level.",
    );
    expect(message).not.toContain("corp-hidden-parent");
  });

  it("explains why unsafe self and cycle edges were omitted", () => {
    expect(customerHierarchyIssueMessage("self_parent_ignored")).toContain(
      "self-parent relationship was ignored",
    );
    expect(customerHierarchyIssueMessage("cycle_parent_ignored")).toContain(
      "parent cycle was ignored",
    );
  });
});

import { describe, expect, it } from "vitest";
import type { CustomerMasterEntity } from "./api";
import { buildCustomerEntityForest, flattenVisibleCustomerTree } from "./customerMasterTree";

function entity(
  id: string,
  parentEntityId: string | null = null,
  level: "Group" | "Company" | "Plant" = "Company",
): CustomerMasterEntity {
  return {
    corporate_entity_id: id,
    corporate_entity_code: id.toUpperCase(),
    entity_name: id,
    entity_level_code: level.toLowerCase(),
    entity_level_label: level,
    parent_entity_id: parentEntityId,
  };
}

describe("buildCustomerEntityForest", () => {
  it("builds a stable group-company-plant hierarchy", () => {
    const forest = buildCustomerEntityForest([
      entity("group", null, "Group"),
      entity("company", "group", "Company"),
      entity("plant", "company", "Plant"),
    ]);

    expect(forest).toHaveLength(1);
    expect(forest[0].entity.corporate_entity_id).toBe("group");
    expect(forest[0].children[0].entity.corporate_entity_id).toBe("company");
    expect(forest[0].children[0].children[0].entity.corporate_entity_id).toBe("plant");
    expect(forest[0].hierarchyIssue).toBeNull();
  });

  it("promotes a missing-parent and self-parent entity instead of hiding it", () => {
    const forest = buildCustomerEntityForest([
      entity("self", "self"),
      entity("orphan", "not-authorized"),
    ]);

    expect(forest.map((node) => node.entity.corporate_entity_id)).toEqual(["self", "orphan"]);
    expect(forest.map((node) => node.hierarchyIssue)).toEqual([
      "self_parent",
      "missing_parent",
    ]);
  });

  it("breaks every member of a cycle into a reviewable root and preserves descendants", () => {
    const forest = buildCustomerEntityForest([
      entity("a", "b"),
      entity("b", "a"),
      entity("child", "a"),
    ]);

    expect(forest.map((node) => node.entity.corporate_entity_id)).toEqual(["a", "b"]);
    expect(forest.map((node) => node.hierarchyIssue)).toEqual(["cycle", "cycle"]);
    expect(forest[0].children.map((node) => node.entity.corporate_entity_id)).toEqual(["child"]);
  });
});

describe("flattenVisibleCustomerTree", () => {
  it("returns WAI-ARIA navigation order and hides collapsed descendants", () => {
    const forest = buildCustomerEntityForest([
      entity("group", null, "Group"),
      entity("company", "group", "Company"),
      entity("plant", "company", "Plant"),
      entity("other", null, "Group"),
    ]);

    expect(
      flattenVisibleCustomerTree(forest, new Set(["group", "company"])).map((item) => ({
        id: item.entityId,
        level: item.level,
        parent: item.parentEntityId,
        position: item.positionInSet,
        setSize: item.setSize,
      })),
    ).toEqual([
      { id: "group", level: 1, parent: null, position: 1, setSize: 2 },
      { id: "company", level: 2, parent: "group", position: 1, setSize: 1 },
      { id: "plant", level: 3, parent: "company", position: 1, setSize: 1 },
      { id: "other", level: 1, parent: null, position: 2, setSize: 2 },
    ]);

    expect(flattenVisibleCustomerTree(forest, new Set()).map((item) => item.entityId)).toEqual([
      "group",
      "other",
    ]);
  });
});

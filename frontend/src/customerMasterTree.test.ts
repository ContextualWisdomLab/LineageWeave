import { describe, expect, it } from "vitest";
import type { CustomerMasterEntity } from "./api";
import { buildCustomerEntityTree } from "./customerMasterTree";

function entity(
  corporate_entity_id: string,
  entity_name: string,
  parent_entity_id: string | null,
): CustomerMasterEntity {
  return {
    corporate_entity_id,
    corporate_entity_code: corporate_entity_id.toUpperCase(),
    entity_name,
    entity_level_code: "company",
    entity_level_label: "Company",
    parent_entity_id,
  };
}

describe("buildCustomerEntityTree", () => {
  it("keeps self-parent and unavailable-parent entities visible with disclosure", () => {
    const forest = buildCustomerEntityTree([
      entity("self", "Self Parent", "self"),
      entity("orphan", "Orphan", "missing"),
    ]);

    expect(forest.map((node) => [node.entity.corporate_entity_id, node.hierarchyIssue])).toEqual([
      ["orphan", "parent_not_available"],
      ["self", "self_parent_ignored"],
    ]);
  });

  it("discloses an empty malformed parent identity instead of treating it as a root", () => {
    const forest = buildCustomerEntityTree([
      entity("malformed-parent", "Malformed parent", ""),
    ]);

    expect(forest).toHaveLength(1);
    expect(forest[0].entity.corporate_entity_id).toBe("malformed-parent");
    expect(forest[0].hierarchyIssue).toBe("parent_not_available");
  });

  it("breaks a pure cycle deterministically without dropping either entity", () => {
    const alpha = entity("alpha", "Alpha", "beta");
    const beta = entity("beta", "Beta", "alpha");

    const forward = buildCustomerEntityTree([alpha, beta]);
    const reversed = buildCustomerEntityTree([beta, alpha]);

    for (const forest of [forward, reversed]) {
      expect(forest).toHaveLength(1);
      expect(forest[0].entity.corporate_entity_id).toBe("alpha");
      expect(forest[0].hierarchyIssue).toBe("cycle_parent_ignored");
      expect(forest[0].children.map((node) => node.entity.corporate_entity_id)).toEqual(["beta"]);
    }
  });

  it("rejects duplicate corporate entity identities instead of choosing one row", () => {
    expect(() =>
      buildCustomerEntityTree([
        entity("duplicate", "Original entity", null),
        entity("duplicate", "Conflicting entity", null),
      ]),
    ).toThrow("duplicate corporate_entity_id: duplicate");
  });

  it("rejects blank canonical entity identities instead of rendering anonymous roots", () => {
    for (const malformedId of ["", "   "]) {
      expect(() =>
        buildCustomerEntityTree([
          entity(malformedId, "Missing canonical identity", null),
        ]),
      ).toThrow("corporate_entity_id must be a non-blank string");
    }
  });

  it("rejects surrounding whitespace in canonical entity identities instead of creating aliases", () => {
    for (const malformedId of [" entity-id", "entity-id ", "\tentity-id", "entity-id\n"]) {
      expect(() =>
        buildCustomerEntityTree([
          entity(malformedId, "Aliased canonical identity", null),
        ]),
      ).toThrow("corporate_entity_id must not contain surrounding whitespace");
    }
  });

  it("keeps ordinary parent-child structure deterministic", () => {
    const parent = entity("parent", "Parent", null);
    const childB = entity("child-b", "Child B", "parent");
    const childA = entity("child-a", "Child A", "parent");

    const forest = buildCustomerEntityTree([childB, parent, childA]);

    expect(forest).toHaveLength(1);
    expect(forest[0].entity.corporate_entity_id).toBe("parent");
    expect(forest[0].hierarchyIssue).toBeNull();
    expect(forest[0].children.map((node) => node.entity.corporate_entity_id)).toEqual([
      "child-a",
      "child-b",
    ]);
  });
});

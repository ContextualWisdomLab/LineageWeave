import { describe, expect, it } from "vitest";
import type { CustomerMasterEntity, CustomerMasterResponse } from "./api";
import { projectCustomerMasterResponse } from "./customerMasterProjection";

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

function response(corporate_entities: CustomerMasterEntity[]): CustomerMasterResponse {
  return {
    corporate_entities,
    relationship_network: [],
    source_customer_hints: [],
    source_author_hints: [],
    keymen: [],
  };
}

describe("projectCustomerMasterResponse", () => {
  it("makes ignored hierarchy edges visible without mutating source entities", () => {
    const self = entity("self", "Self Parent", "self");
    const orphan = entity("orphan", "Orphan", "missing");
    const raw = response([self, orphan]);

    const projected = projectCustomerMasterResponse(raw);

    expect(self.parent_entity_id).toBe("self");
    expect(self.entity_level_label).toBe("Company");
    expect(projected.corporate_entities).toEqual([
      expect.objectContaining({
        corporate_entity_id: "orphan",
        parent_entity_id: null,
        entity_level_code: "company",
        entity_level_label: "Company · Parent not available in this authorized view",
      }),
      expect.objectContaining({
        corporate_entity_id: "self",
        parent_entity_id: null,
        entity_level_code: "company",
        entity_level_label: "Company · Self-parent link omitted",
      }),
    ]);
  });

  it("projects a pure cycle as one deterministic visible root", () => {
    const projected = projectCustomerMasterResponse(
      response([
        entity("beta", "Beta", "alpha"),
        entity("alpha", "Alpha", "beta"),
      ]),
    );

    expect(projected.corporate_entities).toEqual([
      expect.objectContaining({
        corporate_entity_id: "alpha",
        parent_entity_id: null,
        entity_level_label: "Company · Cyclic parent link omitted",
      }),
      expect.objectContaining({
        corporate_entity_id: "beta",
        parent_entity_id: "alpha",
        entity_level_label: "Company",
      }),
    ]);
  });
});

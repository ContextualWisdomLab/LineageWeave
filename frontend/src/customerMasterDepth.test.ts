import { describe, expect, it } from "vitest";
import type { CustomerMasterEntity, CustomerMasterResponse } from "./apiTransport";
import { projectCustomerMasterResponse } from "./customerMasterProjection";

function deepHierarchy(depth: number): CustomerMasterEntity[] {
  return Array.from({ length: depth }, (_, index) => ({
    corporate_entity_id: `entity-${index.toString().padStart(5, "0")}`,
    corporate_entity_code: `ENTITY_${index}`,
    entity_name: `Entity ${index.toString().padStart(5, "0")}`,
    entity_level_code: "company",
    entity_level_label: "Company",
    parent_entity_id:
      index === 0 ? null : `entity-${(index - 1).toString().padStart(5, "0")}`,
  }));
}

describe("Customer Master deep hierarchy", () => {
  it("projects a deep authorized hierarchy without recursive call-stack failure", () => {
    const response: CustomerMasterResponse = {
      corporate_entities: deepHierarchy(12_000),
      keymen: [],
      source_customer_hints: [],
      source_author_hints: [],
      relationship_network: [],
    };

    const projected = projectCustomerMasterResponse(response);

    expect(projected.corporate_entities).toHaveLength(12_000);
    expect(projected.corporate_entities[0].corporate_entity_id).toBe("entity-00000");
    expect(projected.corporate_entities.at(-1)?.corporate_entity_id).toBe("entity-11999");
    expect(projected.corporate_entities.at(-1)?.parent_entity_id).toBe("entity-11998");
  });
});

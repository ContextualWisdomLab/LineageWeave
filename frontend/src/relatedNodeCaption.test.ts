import { describe, expect, it } from "vitest";
import type { RelatedNode } from "./api";
import {
  relatedNodeCaption,
  relatedNodeChipAccessibleName,
} from "./relatedNodeCaption";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

describe("relatedNodeCaption", () => {
  it("names a unique affiliation and side", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Ada West",
          person_side_label: "Our side",
          affiliation_organization_name: "Demo Corp",
        }),
      ),
    ).toBe("Ada West, Demo Corp (Our side)");
  });

  it("keeps a side-only chip when no single org is known", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Priya Nair",
          person_side_label: "Counterparty",
        }),
      ),
    ).toBe("Priya Nair (Counterparty)");
  });

  it("names the organization level, not the ontology class", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_corporate_entity",
          label: "Demo Corp",
          entity_level_label: "Company",
        }),
      ),
    ).toBe("Demo Corp (Company)");
  });

  it("falls back to raw authorized codes when lookup labels are absent", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Synthetic Person",
          person_side_code: "SIDE_EXTERNAL",
        }),
      ),
    ).toBe("Synthetic Person (SIDE_EXTERNAL)");

    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_corporate_entity",
          label: "Synthetic Organization",
          entity_level_code: "LEVEL_COMPANY",
        }),
      ),
    ).toBe("Synthetic Organization (LEVEL_COMPANY)");
  });

  it("shows a post title only", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_post",
          label: "Linked post",
        }),
      ),
    ).toBe("Linked post");
  });
});

describe("relatedNodeChipAccessibleName", () => {
  it("contains the visible caption for a walk chip", () => {
    expect(
      relatedNodeChipAccessibleName("Ada West, Demo Corp (Our side)", "walk_person"),
    ).toBe("Related nodes for Ada West, Demo Corp (Our side)");
  });

  it("names the next action on a post chip", () => {
    expect(relatedNodeChipAccessibleName("Linked post", "open_post")).toBe(
      "Open related post: Linked post",
    );
  });
});

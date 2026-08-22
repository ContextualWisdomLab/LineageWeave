import { describe, expect, it } from "vitest";
import type { RelatedNode } from "./api";
import { relatedAffiliationNextAction, relatedNodeCaption } from "./relatedNodeCaption";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

describe("relatedNodeCaption", () => {
  it("names the side and unique org so the next click is a business walk", () => {
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

  it("names a known-plural set so the next action is the Keyman list", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Priya Nair",
          person_side_code: "counterparty",
          person_side_label: "Counterparty",
          affiliation_ambiguous: true,
        }),
      ),
    ).toBe("Priya Nair, multiple organizations (Counterparty)");
  });

  it("keeps a person with no affiliation side-only", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Priya Nair",
          person_side_code: "counterparty",
          person_side_label: "Counterparty",
        }),
      ),
    ).toBe("Priya Nair (Counterparty)");
  });

  it("keeps a unique org when the side label is missing", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Ada West",
          affiliation_organization_name: "Demo Corp",
          ontology_label: "Person",
        }),
      ),
    ).toBe("Ada West, Demo Corp");
  });

  it("prefers the plural signal when a name is also present", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_person",
          label: "Priya Nair",
          person_side_label: "Counterparty",
          affiliation_organization_name: "Northridge Grid",
          affiliation_ambiguous: true,
        }),
      ),
    ).toBe("Priya Nair, multiple organizations (Counterparty)");
  });

  it("tells the reader to read the Keyman list when it is already on screen", () => {
    expect(relatedAffiliationNextAction(true)).toBe(
      "Multiple organizations are recorded. Read every organization in the Keyman list above, then continue the walk.",
    );
  });

  it("tells the reader to extract Keymen when the list is empty", () => {
    expect(relatedAffiliationNextAction(false)).toBe(
      "Multiple organizations are recorded. Extract Keymen to list every organization, then continue the walk.",
    );
  });

  it("uses the entity-level label on organization chips", () => {
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

  it("shows the post title only", () => {
    expect(
      relatedNodeCaption(
        node({
          node_type_code: "node_post",
          label: "Linked post",
          ontology_label: "Post",
        }),
      ),
    ).toBe("Linked post");
  });
});

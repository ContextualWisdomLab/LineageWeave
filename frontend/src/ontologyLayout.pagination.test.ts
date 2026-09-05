import { describe, expect, it } from "vitest";
import type { OntologyNeighborhoodPayload } from "./api";
import { accumulateNeighborhoodPages } from "./ontologyLayout";

const SUBJECT = "https://contextualwisdomlab.github.io/LineageWeave/ontology#node/node_post/synthetic-post";
const LABEL = "http://www.w3.org/2000/01/rdf-schema#label";

function page(value: Record<string, string>): OntologyNeighborhoodPayload {
  return {
    focus_node_id: "synthetic-post",
    focus_node_type_code: "node_post",
    truncated: false,
    next_cursor: null,
    limitation_code: null,
    nodes: [],
    edges: [],
    exact_value_rows: [],
    jsonld: {
      "@graph": [{ "@id": SUBJECT, [LABEL]: value }],
    },
  };
}

describe("ontology pagination JSON-LD identity", () => {
  it("deduplicates equivalent object values when member order changes", () => {
    const firstValue = { "@value": "Synthetic label", "@language": "en" };
    const reorderedValue = { "@language": "en", "@value": "Synthetic label" };

    const merged = accumulateNeighborhoodPages(page(firstValue), page(reorderedValue));

    expect(merged.jsonld["@graph"]).toEqual([
      { "@id": SUBJECT, [LABEL]: firstValue },
    ]);
  });
});

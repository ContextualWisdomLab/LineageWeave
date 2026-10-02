import { describe, expect, it } from "vitest";
import type { OntologyNeighborhoodPayload } from "./api";
import {
  accumulateNeighborhoodPages,
  filterNeighborhood,
  layoutOntologyNeighborhood,
  neighborhoodCsv,
} from "./ontologyLayout";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const EVIDENCE_POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";
const CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1";
const ONTOLOGY_NAMESPACE = "https://contextualwisdomlab.github.io/LineageWeave/ontology#";

function payload(): OntologyNeighborhoodPayload {
  return {
    focus_node_id: POST_ID,
    focus_node_type_code: "node_post",
    truncated: false,
    next_cursor: null,
    limitation_code: null,
    nodes: [
      {
        node_id: POST_ID,
        node_type_code: "node_post",
        ontology_class_iri: "https://example.test/Post",
        display_label: "Demo public post",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        evidence_count: 1,
        shape_code: "rectangle",
      },
      {
        node_id: PERSON_ID,
        node_type_code: "node_person",
        ontology_class_iri: "https://example.test/Person",
        display_label: "Test Person",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        evidence_count: 1,
        shape_code: "ellipse",
      },
      {
        node_id: CORP_ID,
        node_type_code: "node_corporate_entity",
        ontology_class_iri: "https://example.test/CorporateEntity",
        display_label: "Demo Corp",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        evidence_count: 1,
        shape_code: "hexagon",
      },
    ],
    edges: [
      {
        edge_id: "mentions:post-person",
        source_node_type_code: "node_post",
        source_node_id: POST_ID,
        target_node_type_code: "node_person",
        target_node_id: PERSON_ID,
        property_code: "mentions",
        ontology_property_iri: "https://example.test/mentions",
        property_label: "mentions",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        provenance_reference: "knowledge_graph_edge",
        evidence_references: [POST_ID],
      },
      {
        edge_id: "affiliated:person-corp",
        source_node_type_code: "node_person",
        source_node_id: PERSON_ID,
        target_node_type_code: "node_corporate_entity",
        target_node_id: CORP_ID,
        property_code: "affiliatedWith",
        ontology_property_iri: "https://example.test/affiliatedWith",
        property_label: "affiliated with",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        provenance_reference: "knowledge_graph_edge",
        evidence_references: [POST_ID],
      },
    ],
    exact_value_rows: [
      {
        edge_id: "mentions:post-person",
        source_node_id: POST_ID,
        source_label: "Demo public post",
        source_type_code: "node_post",
        property_code: "mentions",
        property_label: "mentions",
        ontology_property_iri: "https://example.test/mentions",
        target_node_id: PERSON_ID,
        target_label: "Test Person",
        target_type_code: "node_person",
        truth_status_code: "truth_observed",
        recorded_at: "2026-01-10T12:00:00+00:00",
        valid_from: "",
        valid_to: "",
        evidence_count: "1",
      },
    ],
    jsonld: { "@graph": [] },
  };
}

describe("ontologyLayout", () => {
  it("keeps evidence-bearing voice assignments in CSV, filters, and page accumulation", () => {
    const source = payload();
    const assignment = {
      post_id: POST_ID,
      voice_type_code: "voc_customer",
      voice_type_iri: "https://example.test/voice/customer",
      voice_type_label: "Voice of Customer",
      is_primary: false,
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "Evidence-backed additional voice",
      evidence_post_id: EVIDENCE_POST_ID,
    };
    const row = {
      ...source.exact_value_rows[0],
      edge_id: `voice-assignment:${POST_ID}:voc_customer`,
      property_code: "hasVoiceAssignment",
      property_label: "Voice carried by this post",
      target_node_id: assignment.voice_type_code,
      target_label: assignment.voice_type_label,
      target_type_code: "node_voice_type",
      evidence_post_id: EVIDENCE_POST_ID,
    };
    const withVoice = {
      ...source,
      voice_assignments: [assignment],
      exact_value_rows: [...source.exact_value_rows, row],
      jsonld: {
        "@graph": [
          { "@id": `${ONTOLOGY_NAMESPACE}voice-assignment/${POST_ID}/voc_customer` },
          { "@id": assignment.voice_type_iri },
        ],
      },
    } satisfies OntologyNeighborhoodPayload;

    const csv = neighborhoodCsv(withVoice);
    expect(csv).toContain("Voice of Customer");
    expect(csv.split("\n")[0]).toBe(
      "edge_id,source_label,property_label,target_label,truth_status_code,recorded_at,ontology_property_iri,evidence_post_id,carrying_post_id,derivation_evidence_post_id",
    );
    expect(csv).toContain(POST_ID);
    const voiceCsvRow = csv.split("\n").find((row) => row.includes("Voice of Customer"));
    expect(voiceCsvRow).toContain(`${EVIDENCE_POST_ID},${POST_ID},${EVIDENCE_POST_ID}`);
    expect(filterNeighborhood(withVoice, "customer")!.voice_assignments).toEqual([assignment]);
    expect(filterNeighborhood(withVoice, "missing")!.voice_assignments).toEqual([assignment]);
    expect(accumulateNeighborhoodPages(source, withVoice).voice_assignments).toEqual([assignment]);
  });

  it("does not label imported primary evidence as derivation evidence in CSV", () => {
    const source = payload();
    const primary = {
      post_id: POST_ID,
      voice_type_code: "voc_customer",
      voice_type_iri: "https://example.test/voice/customer",
      voice_type_label: "Voice of Customer",
      is_primary: true,
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "Imported primary voice",
      evidence_post_id: POST_ID,
    };
    const primaryRow = {
      ...source.exact_value_rows[0],
      edge_id: `voice-assignment:${POST_ID}:voc_customer`,
      property_code: "hasVoiceAssignment",
      property_label: "Voice carried by this post",
      target_node_id: primary.voice_type_code,
      target_label: primary.voice_type_label,
      target_type_code: "node_voice_type",
      evidence_post_id: POST_ID,
    };

    const csv = neighborhoodCsv({
      ...source,
      voice_assignments: [primary],
      exact_value_rows: [primaryRow],
    });

    expect(csv.split("\n")[1].split(",").slice(-3)).toEqual([
      POST_ID,
      POST_ID,
      "",
    ]);
  });

  it("exports additional Voice derivation evidence from the assignment authority", () => {
    const source = payload();
    const assignment = {
      post_id: POST_ID,
      voice_type_code: "voc_customer",
      voice_type_iri: "https://example.test/voice/customer",
      voice_type_label: "Voice of Customer",
      is_primary: false,
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "prov:assignment",
      evidence_post_id: EVIDENCE_POST_ID,
    };
    const voiceRow = {
      ...source.exact_value_rows[0],
      edge_id: `voice-assignment:${POST_ID}:voc_customer`,
      property_code: "hasVoiceAssignment",
      property_label: "Voice carried by this post",
      target_node_id: assignment.voice_type_code,
      target_label: assignment.voice_type_label,
      target_type_code: "node_voice_type",
      evidence_post_id: undefined,
    };

    const csv = neighborhoodCsv({
      ...source,
      voice_assignments: [assignment],
      exact_value_rows: [voiceRow],
    });

    expect(csv.split("\n")[1].split(",").slice(-3)).toEqual([
      "",
      POST_ID,
      EVIDENCE_POST_ID,
    ]);
  });

  it("merges JSON-LD properties and multi-value relations for one paged subject", () => {
    const source = payload();
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const propertyIri = `${ONTOLOGY_NAMESPACE}hasVoiceAssignment`;
    const first = {
      ...source,
      jsonld: { "@graph": [{ "@id": postIri, "rdfs:label": "Demo public post", [propertyIri]: [{ "@id": "voice:one" }] }] },
    };
    const second = {
      ...source,
      jsonld: { "@graph": [{ "@id": postIri, [propertyIri]: [{ "@id": "voice:two" }] }] },
    };

    expect(accumulateNeighborhoodPages(first, second).jsonld["@graph"]).toEqual([
      {
        "@id": postIri,
        "rdfs:label": "Demo public post",
        [propertyIri]: [{ "@id": "voice:one" }, { "@id": "voice:two" }],
      },
    ]);
  });

  it("keeps only exact canonical JSON-LD node ids when filtering", () => {
    const source = payload();
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const filtered = filterNeighborhood({
      ...source,
      jsonld: {
        "@graph": [
          { "@id": postIri },
          { "@id": `https://example.test/prefix/${postIri}` },
        ],
      },
    }, "missing")!;

    expect(filtered.jsonld["@graph"]).toEqual([{ "@id": postIri }]);
  });

  it("matches the backend's canonical encoding for node ids", () => {
    const source = payload();
    const nodeId = `${POST_ID}/operator's-plan`;
    const nodeIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}/operator%27s-plan`;
    const filtered = filterNeighborhood({
      ...source,
      focus_node_id: nodeId,
      nodes: [{ ...source.nodes[0], node_id: nodeId }],
      edges: [],
      exact_value_rows: [],
      jsonld: { "@graph": [{ "@id": nodeIri }] },
    }, "missing")!;

    expect(filtered.jsonld["@graph"]).toEqual([{ "@id": nodeIri }]);
  });

  it("is deterministic for a fixed payload", () => {
    const first = layoutOntologyNeighborhood(payload());
    const second = layoutOntologyNeighborhood(payload());
    expect(first).toEqual(second);
    expect(first.nodes[0].node_id).toBe(POST_ID);
    expect(new Set(first.nodes.map((node) => `${node.x},${node.y}`)).size).toBe(first.nodes.length);
  });

  it("keeps node identity typed when identifiers collide across catalogs", () => {
    const source = payload();
    const collided: OntologyNeighborhoodPayload = {
      ...source,
      nodes: source.nodes.map((node) =>
        node.node_type_code === "node_person" ? { ...node, node_id: POST_ID } : node,
      ),
      edges: source.edges.map((edge) =>
        edge.source_node_type_code === "node_person" || edge.target_node_type_code === "node_person"
          ? {
              ...edge,
              source_node_id: edge.source_node_type_code === "node_person" ? POST_ID : edge.source_node_id,
              target_node_id: edge.target_node_type_code === "node_person" ? POST_ID : edge.target_node_id,
            }
          : edge,
      ),
    };
    const layout = layoutOntologyNeighborhood(collided);
    expect(layout.nodes).toHaveLength(3);
    expect(layout.edges).toHaveLength(2);
  });

  it("exports CSV without leaking omitted counts", () => {
    const csv = neighborhoodCsv(payload());
    expect(csv).toContain("Demo public post");
    expect(csv.toLowerCase()).not.toContain("omitted");
    expect(neighborhoodCsv({ ...payload(), exact_value_rows: [] })).toMatch(/^edge_id,/);
    const quoted = neighborhoodCsv({
      ...payload(),
      exact_value_rows: [
        {
          ...payload().exact_value_rows[0],
          source_label: 'Demo, "quoted" post',
        },
      ],
    });
    expect(quoted).toContain('"Demo, ""quoted"" post"');
    const formula = neighborhoodCsv({
      ...payload(),
      exact_value_rows: [
        {
          ...payload().exact_value_rows[0],
          source_label: "=1+1",
        },
      ],
    });
    expect(formula).toContain("'=1+1");
  });

  it("uses code-unit ordering instead of the runtime locale", () => {
    const unordered = payload();
    const laidOut = layoutOntologyNeighborhood({
      ...unordered,
      edges: [],
      exact_value_rows: [],
      nodes: [
        { ...unordered.nodes[0], display_label: "Focus" },
        { ...unordered.nodes[1], display_label: "ä" },
        { ...unordered.nodes[2], display_label: "z" },
      ],
    });
    const byId = new Map(laidOut.nodes.map((node) => [node.node_id, node]));
    expect(byId.get(CORP_ID)!.y).toBeLessThan(byId.get(PERSON_ID)!.y);
  });

  it("accumulates later pages without dropping earlier edges", () => {
    const first = payload();
    const secondEdge = first.edges[1];
    const second: OntologyNeighborhoodPayload = {
      ...first,
      truncated: false,
      next_cursor: null,
      nodes: [first.nodes[2]],
      edges: [secondEdge],
      exact_value_rows: [
        {
          ...first.exact_value_rows[0],
          edge_id: secondEdge.edge_id,
          source_node_id: PERSON_ID,
          source_label: "Test Person",
          target_node_id: CORP_ID,
          target_label: "Demo Corp",
        },
      ],
      jsonld: {
        "@graph": [{ "@id": `lw:edge/${secondEdge.edge_id}` }],
      },
    };
    const merged = accumulateNeighborhoodPages(first, second);
    expect(merged.edges.map((edge) => edge.edge_id)).toEqual([
      first.edges[0].edge_id,
      first.edges[1].edge_id,
    ]);
    expect(merged.nodes).toHaveLength(3);
    expect(merged.next_cursor).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import type { OntologyNeighborhoodPayload } from "./api";
import {
  accumulateNeighborhoodPages,
  filterNeighborhood,
  layoutOntologyNeighborhood,
  neighborhoodCsv,
} from "./ontologyLayout";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
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
      evidence_post_id: POST_ID,
    };
    const row = {
      ...source.exact_value_rows[0],
      edge_id: `voice-assignment:${POST_ID}:voc_customer`,
      property_code: "hasVoiceAssignment",
      property_label: "Voice carried by this post",
      target_node_id: assignment.voice_type_code,
      target_label: assignment.voice_type_label,
      target_type_code: "node_voice_type",
      evidence_post_id: POST_ID,
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
    expect(csv.split("\n")[0]).toContain("evidence_post_id");
    expect(csv.split("\n")[0]).toContain("carrying_post_id");
    expect(csv.split("\n")[0]).toContain("derivation_evidence_post_id");
    expect(csv).toContain(POST_ID);
    expect(filterNeighborhood(withVoice, "customer")!.voice_assignments).toEqual([assignment]);
    expect(filterNeighborhood(withVoice, "missing")!.voice_assignments).toEqual([assignment]);
    expect(accumulateNeighborhoodPages(source, withVoice).voice_assignments).toEqual([assignment]);
  });

  it("omits derived voices when a search hides their evidence post", () => {
    const source = payload();
    const evidenceId = "dddddddd-dddd-dddd-dddd-ddddddddddd1";
    const assignmentIri = `${ONTOLOGY_NAMESPACE}voice-assignment/${POST_ID}/vops`;
    const primaryIri = `${ONTOLOGY_NAMESPACE}voice-assignment/${POST_ID}/voc`;
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const evidenceIri = `${ONTOLOGY_NAMESPACE}node/node_post/${evidenceId}`;
    const relation = `${ONTOLOGY_NAMESPACE}hasVoiceAssignment`;
    const assignment = {
      post_id: POST_ID,
      voice_type_code: "vops",
      voice_type_iri: `${ONTOLOGY_NAMESPACE}voiceOfProcessType`,
      voice_type_label: "Voice of Process",
      is_primary: false,
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "Evidence-backed additional voice",
      evidence_post_id: evidenceId,
    };
    const primary = {
      ...assignment,
      voice_type_code: "voc",
      voice_type_iri: `${ONTOLOGY_NAMESPACE}voiceOfCustomerType`,
      voice_type_label: "Voice of Customer",
      is_primary: true,
      evidence_post_id: null,
    };
    const row = {
      ...source.exact_value_rows[0],
      edge_id: `voice-assignment:${POST_ID}:vops`,
      property_code: "hasVoiceAssignment",
      evidence_post_id: evidenceId,
    };
    const withVoice = {
      ...source,
      nodes: [source.nodes[0], { ...source.nodes[0], node_id: evidenceId, display_label: "Evidence source" }],
      edges: [],
      exact_value_rows: [row, { ...row, edge_id: `voice-assignment:${POST_ID}:voc`, evidence_post_id: POST_ID }],
      voice_assignments: [assignment, primary],
      jsonld: { "@graph": [
        { "@id": postIri, "rdfs:label": "Carrying post", [relation]: [
          { "@id": assignmentIri }, { "@id": primaryIri },
        ] },
        { "@id": evidenceIri },
        { "@id": assignmentIri, "prov:wasDerivedFrom": { "@id": evidenceIri } },
        { "@id": primaryIri, "prov:wasDerivedFrom": { "@id": postIri } },
        { "@id": assignment.voice_type_iri },
        { "@id": primary.voice_type_iri },
      ] },
    } satisfies OntologyNeighborhoodPayload;

    const hidden = filterNeighborhood(withVoice, "no match")!;
    expect(hidden.voice_assignments).toEqual([primary]);
    expect(hidden.exact_value_rows.map((value) => value.edge_id)).toEqual([
      `voice-assignment:${POST_ID}:voc`,
    ]);
    expect(hidden.jsonld["@graph"]).toEqual([
      { "@id": postIri, "rdfs:label": "Carrying post", [relation]: [{ "@id": primaryIri }] },
      { "@id": primaryIri, "prov:wasDerivedFrom": { "@id": postIri } },
      { "@id": primary.voice_type_iri },
    ]);

    const shown = filterNeighborhood(withVoice, "Evidence source")!;
    expect(shown.voice_assignments).toEqual([assignment, primary]);
    expect(shown.exact_value_rows.map((value) => value.edge_id)).toEqual([
      row.edge_id, `voice-assignment:${POST_ID}:voc`,
    ]);
    expect((shown.jsonld["@graph"] as Array<Record<string, unknown>>)[0][relation]).toEqual([
      { "@id": assignmentIri },
      { "@id": primaryIri },
    ]);

    const dangling = filterNeighborhood({
      ...withVoice,
      nodes: [source.nodes[0]],
      edges: [{
        ...source.edges[0],
        edge_id: "dangling-evidence-reference",
        source_node_type_code: "node_post",
        source_node_id: POST_ID,
        target_node_type_code: "node_post",
        target_node_id: evidenceId,
        property_label: "related evidence",
      }],
    }, "related evidence")!;
    expect(dangling.edges).toEqual([]);
    expect(dangling.voice_assignments).toEqual([primary]);
    expect(dangling.exact_value_rows.map((value) => value.edge_id)).toEqual([
      `voice-assignment:${POST_ID}:voc`,
    ]);
    expect((dangling.jsonld["@graph"] as Array<Record<string, unknown>>)[0][relation]).toEqual([
      { "@id": primaryIri },
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

  it.each([
    [{ "@id": "voice:one" }, { "@id": "voice:two" }],
    [[{ "@id": "voice:one" }], { "@id": "voice:two" }],
    [{ "@id": "voice:one" }, [{ "@id": "voice:two" }]],
  ])("preserves singleton and array relations across pages (%j, %j)", (previous, added) => {
    const source = payload();
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const propertyIri = `${ONTOLOGY_NAMESPACE}hasVoiceAssignment`;
    const first = { ...source, jsonld: { "@graph": [{ "@id": postIri, [propertyIri]: previous }] } };
    const second = { ...source, jsonld: { "@graph": [{ "@id": postIri, [propertyIri]: added }] } };
    const combined = accumulateNeighborhoodPages(first, second);
    expect(combined.jsonld["@graph"]).toEqual([
      { "@id": postIri, [propertyIri]: [{ "@id": "voice:one" }, { "@id": "voice:two" }] },
    ]);
    expect(accumulateNeighborhoodPages(combined, second).jsonld).toEqual(combined.jsonld);
    expect(first.jsonld["@graph"][0][propertyIri]).toEqual(previous);
  });

  it("removes a hidden singleton Voice reference without replacing its evidence", () => {
    const source = payload();
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const propertyIri = `${ONTOLOGY_NAMESPACE}hasVoiceAssignment`;
    const hiddenIri = `${ONTOLOGY_NAMESPACE}voice-assignment/${POST_ID}/vops`;
    const filtered = filterNeighborhood({
      ...source,
      voice_assignments: [],
      jsonld: { "@graph": [{ "@id": postIri, [propertyIri]: { "@id": hiddenIri } }] },
    }, "missing")!;
    expect(filtered.jsonld["@graph"]).toEqual([{ "@id": postIri }]);
    expect(JSON.stringify(filtered)).not.toContain(hiddenIri);
  });

  it("unions repeated subject types and literal properties without mutating either page", () => {
    const source = payload();
    const postIri = `${ONTOLOGY_NAMESPACE}node/node_post/${POST_ID}`;
    const first = { ...source, jsonld: { "@graph": [{
      "@id": postIri,
      "@type": `${ONTOLOGY_NAMESPACE}Post`,
      "rdfs:label": { "@value": "Synthetic record", "@language": "en" },
    }] } };
    const second = { ...source, jsonld: { "@graph": [{
      "@id": postIri,
      "@type": [`${ONTOLOGY_NAMESPACE}Post`, "http://www.w3.org/ns/prov#Entity"],
      "rdfs:label": { "@value": "합성 기록", "@language": "ko" },
    }] } };
    expect(accumulateNeighborhoodPages(first, second).jsonld["@graph"]).toEqual([{
      "@id": postIri,
      "@type": [`${ONTOLOGY_NAMESPACE}Post`, "http://www.w3.org/ns/prov#Entity"],
      "rdfs:label": [first.jsonld["@graph"][0]["rdfs:label"], second.jsonld["@graph"][0]["rdfs:label"]],
    }]);
    expect(first.jsonld["@graph"][0]["@type"]).toBe(`${ONTOLOGY_NAMESPACE}Post`);
  });

  it("exports distinct carrying and derivation identities with the recorded interval", () => {
    const source = payload();
    const evidenceId = "dddddddd-dddd-dddd-dddd-ddddddddddd1";
    const csv = neighborhoodCsv({
      ...source,
      exact_value_rows: [{
        ...source.exact_value_rows[0],
        property_code: "hasVoiceAssignment",
        source_node_id: POST_ID,
        evidence_post_id: evidenceId,
        valid_from: "2026-01-10T12:00:00+00:00",
        valid_to: "2026-01-11T12:00:00+00:00",
      }],
    });
    const [header, row] = csv.trim().split("\n").map((line) => line.split(","));
    const values = Object.fromEntries(header.map((key, index) => [key, row[index]]));
    expect(values).toMatchObject({
      source_node_id: POST_ID,
      evidence_post_id: evidenceId,
      carrying_post_id: POST_ID,
      derivation_evidence_post_id: evidenceId,
      valid_from: "2026-01-10T12:00:00+00:00",
      valid_to: "2026-01-11T12:00:00+00:00",
    });
  });

  it.each(["node_post", "node_person", "node_corporate_entity", "node_team", "node_project"])(
    "does not label a %s relation endpoint as a carrying Voice post",
    (sourceType) => {
      const source = payload();
      const csv = neighborhoodCsv({
        ...source,
        exact_value_rows: [{
          ...source.exact_value_rows[0],
          source_type_code: sourceType,
          evidence_post_id: POST_ID,
        }],
      });
      const [header, row] = csv.trim().split("\n").map((line) => line.split(","));
      const values = Object.fromEntries(header.map((key, index) => [key, row[index]]));
      expect(values).toMatchObject({
        source_node_id: POST_ID,
        source_type_code: sourceType,
        evidence_post_id: POST_ID,
        carrying_post_id: "",
        derivation_evidence_post_id: "",
      });
    },
  );

  it("does not fabricate a carrying Post for an incorrectly typed Voice row", () => {
    const source = payload();
    const csv = neighborhoodCsv({
      ...source,
      exact_value_rows: [{
        ...source.exact_value_rows[0],
        property_code: "hasVoiceAssignment",
        source_type_code: "node_person",
        evidence_post_id: POST_ID,
      }],
    });
    const [header, row] = csv.trim().split("\n").map((line) => line.split(","));
    expect(row[header.indexOf("carrying_post_id")]).toBe("");
    expect(row[header.indexOf("derivation_evidence_post_id")]).toBe("");
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

  it.each([
    [false, false],
    [false, true],
    [true, false],
    [true, true],
  ])("preserves Voice and derivation values across compact page forms (%s, %s)", (firstArray, nextArray) => {
    const first = payload();
    const post = `${ONTOLOGY_NAMESPACE}post/${POST_ID}`;
    const customer = { "@id": `${ONTOLOGY_NAMESPACE}voice-assignment/customer` };
    const employee = { "@id": `${ONTOLOGY_NAMESPACE}voice-assignment/employee` };
    const evidence = { "@id": `${ONTOLOGY_NAMESPACE}post/${PERSON_ID}` };
    const shape = (value: unknown, array: boolean) => array ? [value] : value;
    first.jsonld = { "@graph": [{
      "@id": post,
      "@type": "lw:Post",
      "lw:hasVoiceAssignment": shape(customer, firstArray),
      "prov:wasDerivedFrom": shape(evidence, firstArray),
      "rdfs:label": "Synthetic carrying post",
    }] };
    const next = { ...payload(), jsonld: { "@graph": [{
      "@id": post,
      "@type": ["lw:Post", "prov:Entity"],
      "lw:hasVoiceAssignment": shape(employee, nextArray),
      "prov:wasDerivedFrom": shape(evidence, nextArray),
    }] } };
    const merged = accumulateNeighborhoodPages(first, next);
    expect(merged.jsonld["@graph"]).toEqual([{
      "@id": post,
      "@type": ["lw:Post", "prov:Entity"],
      "lw:hasVoiceAssignment": [customer, employee],
      "prov:wasDerivedFrom": firstArray || nextArray ? [evidence] : evidence,
      "rdfs:label": "Synthetic carrying post",
    }]);
    expect(accumulateNeighborhoodPages(merged, next).jsonld).toEqual(merged.jsonld);
    expect(first.jsonld["@graph"]).toEqual([{
      "@id": post,
      "@type": "lw:Post",
      "lw:hasVoiceAssignment": shape(customer, firstArray),
      "prov:wasDerivedFrom": shape(evidence, firstArray),
      "rdfs:label": "Synthetic carrying post",
    }]);
  });

  it("keeps the latest node label and all JSON-LD values across pages", () => {
    const first = payload();
    const subject = `${ONTOLOGY_NAMESPACE}post/${POST_ID}`;
    const person = { "@id": `${ONTOLOGY_NAMESPACE}person/${PERSON_ID}` };
    const organization = { "@id": `${ONTOLOGY_NAMESPACE}organization/${CORP_ID}` };
    first.jsonld = { "@graph": [{
      "@id": subject, "rdfs:label": "Synthetic draft", "lw:mentions": person,
    }] };
    const next = {
      ...payload(),
      nodes: [{ ...first.nodes[0], display_label: "Synthetic approved" }],
      jsonld: { "@graph": [{
        "@id": subject, "rdfs:label": "Synthetic approved", "lw:mentions": organization,
      }] },
    };
    const merged = accumulateNeighborhoodPages(first, next);
    expect(merged.nodes[0].display_label).toBe("Synthetic approved");
    expect(merged.jsonld["@graph"]).toEqual([{
      "@id": subject,
      "rdfs:label": ["Synthetic draft", "Synthetic approved"],
      "lw:mentions": [person, organization],
    }]);
    expect(accumulateNeighborhoodPages(merged, {
      ...next, jsonld: { "@graph": [{ "@id": subject, "lw:mentions": person }] },
    }).jsonld).toEqual(merged.jsonld);
    expect(first.jsonld["@graph"]).toEqual([{
      "@id": subject, "rdfs:label": "Synthetic draft", "lw:mentions": person,
    }]);
  });

  it("retains both targets when the server emits repeated scalar relations for one subject", () => {
    const first = payload();
    const subject = `${ONTOLOGY_NAMESPACE}post/${POST_ID}`;
    const property = `${ONTOLOGY_NAMESPACE}mentions`;
    const person = { "@id": `${ONTOLOGY_NAMESPACE}person/${PERSON_ID}` };
    const organization = { "@id": `${ONTOLOGY_NAMESPACE}organization/${CORP_ID}` };
    first.jsonld = { "@graph": [
      { "@id": subject, "@type": "lw:Post", "rdfs:label": "Synthetic post" },
      { "@id": subject, [property]: person },
      { "@id": subject, [property]: organization },
    ] };
    const next = { ...payload(), jsonld: { "@graph": [{ "@id": subject, [property]: person }] } };
    expect(accumulateNeighborhoodPages(first, next).jsonld["@graph"]).toEqual([{
      "@id": subject,
      "@type": "lw:Post",
      "rdfs:label": "Synthetic post",
      [property]: [person, organization],
    }]);
  });
});

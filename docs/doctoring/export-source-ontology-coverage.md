# Export-source ontology coverage

Supporting document for [ADR 0246](../adr/0246-export-source-ontology-coverage.md).
Read-only aggregate analysis of an authorized export source against the
published LineageWeave Ontology and Semantic Layer. Per ADR 0001 / ADR 0242
decision 5, only non-identifying aggregate counts and abstract code-set
statements appear below; no source title, person, project name, organization
name, or artifact path is retained.

## Coverage

The export provides short business documents with a governed five-value
document type, a country/region attribute, ERP lifecycle codes, an authored
title/body, a document key, and creator/editor timestamps. The published
ontology covers everything except one derived-semantic location value, which
ADR 0246 closes.

## Mapping summary

| Export dimension | Aggregate observation | Ontology / Semantic Layer mapping | Status |
| --- | --- | --- | --- |
| Document type (`VOC`, `VOCC`, `VOCO`, `VOM`, `VOP`) | five governed codes, 43,814 rows | `:postTypeScheme` (ADR 0207, migrations/0042) | covered |
| Authored title / body | non-empty authored title per row; zero non-empty authored bodies | `:postTitle`, `:postBody` + `:bodyAvailable` (ADR 0240), content-semantic classes (ADR 0242) | covered |
| Country / region attribute | curated ISO-3166-1 letters with a region marker (`EU`) | `:Location` + `:countryCode` (new, ADR 0246) | covered after 0246 |
| Place name the content names | authored location mention | `:Location` + `:locationName` (new, ADR 0246) | covered after 0246 |
| Raw ERP codes (grade, stage, detail status, deletion flag, product-unit codes) | raw code sets, sparse deletion marker | raw instance literals only; `sourceStageCode` / `sourceDetailStateCode` discipline (ADR 0241); `StatusStage` stays concept-level | raw (ungoverned, intentional) |
| Record identity / document number | export-internal key | identity via `prov:wasDerivedFrom` provenance (ADR 0011); not a vocabulary fact | covered |
| Creator / editor + timestamps | per-row attribution | `prov:Agent` / `prov:Person` / `prov:Organization` via `prov_agent_type` (ADR 0207) | covered |

## Relationship to ADR 0242

Same private-data discipline: this document carries only aggregate facts.
The earlier semantic-coverage run spoke to title/body completeness and
event/stage/status/KG-edge density; this document focuses on the ontology
vocabulary itself. Both keep the "raw code stays instance data until its
code system is governed" boundary -- no new lookup category is seeded by the
export audit.

## Standard and literature grounding

- International Organization for Standardization. (2020). *Codes for the
  representation of names of countries and their subdivisions -- Part 1:
  Country code* (ISO 3166-1:2020).
- Cyganiak, D., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 Concepts
  and Abstract Syntax* (W3C Recommendation, 25 February 2014).
  https://www.w3.org/TR/2014/REC-rdf11-concepts-20150225/
- Lebo, J., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
  Ontology* (W3C Recommendation, 30 April 2013).
  https://www.w3.org/TR/2013/REC-prov-o-20130430/
- Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes Constraint
  Language (SHACL)* (W3C Recommendation, 20 July 2017).
  https://www.w3.org/TR/2017/REC-shacl-20170720/
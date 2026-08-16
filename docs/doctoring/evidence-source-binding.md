# Evidence-source binding for VOC excerpts

LineageWeave presents authorized appointment excerpts as customer-utterance
evidence. A click that opens the 원문 drawer must identify the used source
entity. Opening the first unmatched document row would present another event
as if it evidenced the utterance.

## Binding rule

`vocExcerptEvidenceId` and `voc_excerpt_evidence_id` return a drawer guid only
when:

1. the excerpt's own non-URI `source_evidence_id`, `guid`, or `evidence_id`
   already appears in the authorized same-document event set;
2. the document has exactly one event and that event has a usable guid that is
   not the document number; or
3. the excerpt text uniquely matches one same-document event. Date may narrow
   candidates. Date alone does not bind. Empty event blobs do not match.

Ontology HTTP/URN identifiers and leftover usable guids stay non-clickable.
A missing cited guid 404s instead of opening the first source row. Persist
`source_evidence_id` on `analysis_appointment_records` when the bind is unique
so the next 원문 보기 click keeps the same used entity.

## APA 7th sources

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

Sanderson, R., Ciccarese, P., & Young, B. (Eds.). (2017). *Web Annotation data
model*. World Wide Web Consortium. https://www.w3.org/TR/annotation-model/

W3C Provenance Working Group. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/2013/REC-prov-o-20130430/

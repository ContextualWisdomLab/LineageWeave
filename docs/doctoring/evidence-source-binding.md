# Evidence-source binding for VOC excerpts

LineageWeave presents authorized appointment excerpts as customer-utterance
evidence. A click that opens the 원문 drawer must identify the used source
entity. Opening the first unmatched document row would present another event
as if it evidenced the utterance.

## Binding rule

`vocExcerptEvidenceId` returns a drawer guid only when:

1. the excerpt already carries its own non-URI `source_evidence_id`, `guid`,
   or `evidence_id`;
2. the authorized document has exactly one usable event guid; or
3. the excerpt date and/or text uniquely matches one same-document event.

Ontology HTTP/URN identifiers stay non-clickable. Multiple unmatched events
stay static text.

## APA 7th sources

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

Sanderson, R., Ciccarese, P., & Young, B. (Eds.). (2017). *Web Annotation data
model*. World Wide Web Consortium. https://www.w3.org/TR/annotation-model/

W3C Provenance Working Group. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/2013/REC-prov-o-20130430/

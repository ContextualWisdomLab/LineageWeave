# Project lifecycle history: standards and research traceability

## Adopted boundaries

- **RFC 3339:** every API instant includes a UTC offset. Unqualified local time
  is rejected; UTC values serialize with `Z`.
- **OWL-Time:** project events project as temporal entities and responsibility
  assignments as proper intervals. `followsProjectEvent` specializes
  `time:after`.
- **PROV-O:** source posts remain evidence used by events, relations, and
  assignments. The RDF profile does not replace PostgreSQL authorization.
- **Allen interval relations:** overlap and containment are considered when
  calculating responsibility coverage. A nested interval cannot create a
  false handover gap.

## Deliberate non-claims

- `projectRelatedTo` does not mean `causes`.
- A visible-evidence gap does not prove that nobody performed the work.
- Event order does not prove a business process transition unless the stored
  relation explicitly states one.
- Hidden source posts never contribute nodes, relations, assignments, or
  derived gap dates to the Buyer response.

## APA 7th references

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Cox, S., & Little, C. (Eds.). (2017). *Time ontology in OWL* (W3C
Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2017/REC-owl-time-20171019/

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps*
(RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2013/REC-prov-o-20130430/

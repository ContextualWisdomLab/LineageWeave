# Naruon calendar projection references

## Product traceability

| Source | Product decision | Evidence |
|---|---|---|
| RFC 4791 | Do not call the legacy JSON `/events` feed CalDAV; provider DAV behavior belongs to Naruon. | ADR 0038; ADR 0143; issue #336 |
| RFC 6578 | Sync tokens and collection reconciliation are provider-authority concerns, not LineageWeave read-model fields. | ADR 0143; Naruon #978/#998 |
| RFC 5545 | Recurrence occurrence identity, timezone, and all-day semantics must survive the Naruon projection. | Projection v1 schema and parser tests |
| PROV-O | External rows remain `observed`; LineageWeave commitments retain separate authoritative post provenance. | `truth_status_code`; ADR 0143 |
| OWASP API4:2023 | Limit page size, date window, timeout, and response bytes before parsing to constrain resource consumption. | Client bounds; bounded HTTP response tests |

## APA 7th references

Daboo, C., Desruisseaux, B., & Dusseault, L. M. (2007). *Calendaring extensions to WebDAV (CalDAV)* (RFC 4791). RFC Editor. https://doi.org/10.17487/RFC4791

Daboo, C., & Quillaud, A. (2012). *Collection synchronization for Web Distributed Authoring and Versioning (WebDAV)* (RFC 6578). RFC Editor. https://doi.org/10.17487/RFC6578

Desruisseaux, B. (2009). *Internet calendaring and scheduling core object specification (iCalendar)* (RFC 5545). RFC Editor. https://doi.org/10.17487/RFC5545

OWASP Foundation. (2023). *OWASP API Security Top 10—API4:2023 unrestricted resource consumption*. https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*. https://www.w3.org/TR/prov-o/

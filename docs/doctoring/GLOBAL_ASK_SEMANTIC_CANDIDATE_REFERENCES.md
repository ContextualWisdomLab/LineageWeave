# Global Ask semantic candidate research register

ADR 0233 is normative. This register records the adopted platform evidence.

| Decision need | Adopted evidence | Product consequence |
|---|---|---|
| Safe user query parsing | PostgreSQL `websearch_to_tsquery` accepts web-search-style input without syntax errors | The application does not invent a tokenizer or repair grammar |
| Indexed multi-value lookup | PostgreSQL GIN is the native inverted-index access method for full-text search | Matching expression indexes cover each persisted semantic evidence family |
| Provenance and authorization | W3C PROV-O distinguishes evidence influence from an access grant | Candidate IDs remain non-authoritative until the final source boundary authorizes them |

## References

PostgreSQL Global Development Group. (2026). *Controlling text search*.
PostgreSQL 18 documentation.
https://www.postgresql.org/docs/current/textsearch-controls.html

PostgreSQL Global Development Group. (2026). *GIN indexes*.
PostgreSQL 18 documentation. https://www.postgresql.org/docs/current/gin.html

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/

# ADR 0124: Opaque ontology source-window continuation

**Status:** Accepted
**Date:** 2026-08-21
**Issue:** [#363](https://github.com/ContextualWisdomLab/LineageWeave/issues/363)
**Predecessor:** [ADR 0119](0119-ontology-provenance-explorer.md)

**Context:** PR #349 withholds a continuation token when the authorization-safe recursive SQL window is exhausted. The in-memory `after:` cursor can only page facts already loaded, so a buyer cannot inspect every authorized relation in a large neighborhood without fabricating completeness. Issue #363 requires a real database continuation contract that keeps bounds, ABAC, cutoff, and deterministic ordering.

**Decision:**

1. `GET /api/ontology/neighborhood` may return a versioned opaque source cursor (`src.v2.`) in addition to the in-memory `after:` token. The source cursor continues the recursive candidate window with keyset pagination. `OFFSET` is forbidden.
2. The process secret is `ONTOLOGY_SOURCE_CURSOR_SECRET`. It is not an OIDC credential, JWKS key, or orchestrator token. A missing or short secret keeps the current truncated-without-cursor behavior.
3. The token uses AES-GCM authenticated encryption with associated data (cursor prefix/version). Plaintext claims never leave the process. The token must not reveal hidden endpoint IDs, omitted counts, SQL ordering keys, timestamps, or tenant identifiers. The v1 custom HMAC keystream format is not accepted by the current implementation.
4. Claims bind tenant/account scope (HMAC digest only), focus type and canonical UUID, `knowledge_cutoff`, depth/node/edge bounds, allowed property codes, last source key, snapshot time, eligibility digest of the frozen visible-post set, contract version, and expiry (15 minutes).
5. Traversal stays focus-connected BFS proximity, then property/tie-break. Source eligibility, `available_time <= knowledge_cutoff`, snapshot time, and endpoint ABAC run before a relation enters a page. A hidden endpoint removes the relation and cannot change visible totals, cursor shape, or timing metadata.
6. A cursor used with a changed focus, cutoff, filter, limit, tenant, eligibility digest, or contract version fails closed. Concurrent graph changes use the sealed snapshot; they never silently splice two graph versions.
7. Page payloads keep the exact-value table, CSV, JSON-LD, provenance, truth status, and mobile/print equivalents. The explorer may accumulate subsequent pages without losing the selected evidence.

**Consequences:**

- The in-memory `after:` token remains valid for assembler-level paging of an already-loaded window when no process secret is configured.
- Event Lineage, arbitrary SQL/Cypher/SPARQL, and inference-to-authority promotion stay out of scope.

**References**

Krawczyk, H., Bellare, M., & Canetti, R. (1997). *HMAC: Keyed-hashing for message authentication* (RFC 2104). Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc2104

Bellare, M., & Namprempre, C. (2008). Authenticated encryption: Relations among notions and analysis of the generic composition paradigm. *Journal of Cryptology, 21*(4), 469–491. https://doi.org/10.1007/s00145-008-9026-x

Dworkin, M. (2007). *Recommendation for block cipher modes of operation: Galois/Counter Mode (GCM) and GMAC* (NIST Special Publication 800-38D). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-38D

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/prov-o/

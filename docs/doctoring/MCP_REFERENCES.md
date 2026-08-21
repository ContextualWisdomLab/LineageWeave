# MCP, OAuth, CORS, and HTTP-framing references

## Standards and research traceability

| External source | LineageWeave decision | Evidence |
|---|---|---|
| MCP Streamable HTTP transport | Dedicated `/mcp` ASGI resource server; validate every present Origin before authentication | `backend/app/mcp_server.py`; Host/Origin tests |
| MCP Authorization | OAuth protected-resource metadata and bearer validation | `AuthSettings`; unauthenticated HTTP test |
| WHATWG Fetch CORS protocol | Exact configured browser Origins; bounded method/header surface; `Vary: Origin`; preflight before OAuth | `CORSMiddleware`; `tests/test_mcp_cors_preflight.py` |
| RFC 9112 HTTP/1.1 message framing | Reject ambiguous `Content-Length`, `Content-Length` plus `Transfer-Encoding`, mismatches, and over-limit streams before parsing | `backend/app/mcp_admission.py`; request-admission tests |
| RFC 8707 resource indicators | Exact `MCP_AUDIENCE` validation | `KeycloakMcpTokenVerifier`; wrong-audience regression |
| RFC 9728 protected-resource metadata | SDK-generated resource metadata | HTTP `WWW-Authenticate` regression |
| Codex MCP configuration | URL plus bearer-token environment variable; optional OAuth login | `docs/integrations/MCP.md` |
| Retrieval-augmented generation | Retrieve authorized sources, then source-only reason-and-cite | `backend/app/global_ask.py`; `lineageweave.post_chat` |
| FEVER claim verification | Keep Supported / Refuted / insufficient-evidence judgment tied to retrieved evidence, not model memory | `backend/app/global_ask_verification.py`; external-verification regressions |
| Data-boundary minimization | Open-web verification is explicit opt-in; the internal answer body is never a Searxng search query | `global_ask(..., verify_external=false)`; privacy-boundary regression |
| Keycloak startup realm import | Treat `--import-realm` as fresh-environment bootstrap because an existing realm is skipped | `docker/keycloak/entrypoint.sh`; ADR 0127 |
| Keycloak Admin REST protocol-mapper endpoints | Reconcile only the named MCP audience mapper with bounded GET/POST/PUT operations | `backend/app/keycloak_audience_reconciler.py`; persistent-port-change regressions |
| Point-of-disclosure authorization | Re-check live `post_read` and corporate affiliation state before cited image bytes leave the database boundary | `backend/app/global_ask_media.py`; permission-revocation regressions |

The external-verification lane is deliberately distinct from LineageWeave's
internal source authority. A public search result can corroborate or contradict
an answer, but it does not become a `source_post`, does not satisfy RBAC/ABAC,
and cannot replace the internal citation bundle. `supported` and `refuted`
require at least one valid cited external HTTP(S) evidence URL; otherwise the
result is `insufficient_evidence`. This mirrors FEVER's core distinction between
a claim label and the evidence required to justify Supported/Refuted judgments.

Browser admission is also separate from product authorization. Exact Host and
Origin validation runs first; bounded request-body admission runs before OAuth
and SDK JSON parsing; CORS preflight runs without a bearer token; then the
existing OAuth, database RBAC, and per-source ABAC controls run. An HTTP framing
rejection grants no identity and consumes no Global Ask invocation.

The chronological source timeline follows the same retrieval boundary as the
answer, preserving event order without fabricating dates. Inline raster content
follows the RFC 2397 data-URL parsing boundary and remains bounded before MCP
serialization. Citation membership is not treated as a durable authorization
lease: the media query resolves the caller's current database role permission
and affiliation again at the point of byte disclosure.

Keycloak documents that startup import skips a realm that already exists. The
Compose import template therefore bootstraps a new demo realm only. A separate
one-shot reconciler uses the Admin REST protocol-mapper collection and mapper
update endpoints to create or update the dedicated audience mapper while
leaving the persisted realm, users, roles, sessions, and unrelated clients
untouched. The reconciler is bounded, idempotent, and a prerequisite for MCP
startup.

## APA 7th references

Fielding, R. T., Nottingham, M., & Reschke, J. (Eds.). (2022). *HTTP/1.1*
(RFC 9112). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9112

Jones, M., Bradley, J., & Sakimura, N. (2020). *Resource indicators for OAuth
2.0* (RFC 8707). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8707

Keycloak. (n.d.-a). *Importing and exporting realms*. Retrieved August 20,
2026, from https://www.keycloak.org/server/importExport

Keycloak. (n.d.-b). *Keycloak Admin REST API: Protocol mappers*. Retrieved
August 20, 2026, from
https://www.keycloak.org/docs-api/26.0.8/rest-api/index.html

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler,
H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020).
Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances
in Neural Information Processing Systems, 33*, 9459–9474.

Masinter, L. (1998). *The “data” URL scheme* (RFC 2397). Internet Engineering
Task Force. https://doi.org/10.17487/RFC2397

Model Context Protocol. (2026). *Authorization*. Linux Foundation.
https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

Model Context Protocol. (2026). *Transports: Streamable HTTP*. Linux Foundation.
https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

OpenAI. (2026). *Model Context Protocol*. OpenAI Developers.
https://developers.openai.com/codex/mcp/

Parecki, A., Richer, J., & Hunt, P. (2025). *OAuth 2.0 protected resource
metadata* (RFC 9728). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9728

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and VERification. In *Proceedings of
the 2018 Conference of the North American Chapter of the Association for
Computational Linguistics: Human Language Technologies, Volume 1 (Long Papers)*
(pp. 809–819). Association for Computational Linguistics.
https://doi.org/10.18653/v1/N18-1074
WHATWG. (2026). *Fetch* (Living Standard).
https://fetch.spec.whatwg.org/

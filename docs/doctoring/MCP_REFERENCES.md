# MCP and OAuth references

## Standards traceability

| External source | LineageWeave decision | Evidence |
|---|---|---|
| MCP Streamable HTTP transport | Dedicated `/mcp` ASGI resource server | `backend/app/mcp_server.py`; MCP client tests |
| MCP Authorization | OAuth protected-resource metadata and bearer validation | `AuthSettings`; unauthenticated HTTP test |
| RFC 8707 resource indicators | Exact `MCP_AUDIENCE` validation | `KeycloakMcpTokenVerifier`; wrong-audience regression |
| RFC 9728 protected-resource metadata | SDK-generated resource metadata | HTTP `WWW-Authenticate` regression |
| Codex MCP configuration | URL plus bearer-token environment variable; optional OAuth login | `docs/integrations/MCP.md` |
| Retrieval-augmented generation | Retrieve authorized sources, then source-only reason-and-cite | `backend/app/global_ask.py`; existing `lineageweave.post_chat` |

## APA 7th references

Jones, M., Bradley, J., & Sakimura, N. (2020). *Resource indicators for OAuth
2.0* (RFC 8707). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8707

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler,
H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020).
Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances
in Neural Information Processing Systems, 33*, 9459–9474.

Model Context Protocol. (2026). *Authorization*. Linux Foundation.
https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

OpenAI. (2026). *Model Context Protocol*. OpenAI Developers.
https://developers.openai.com/codex/mcp/

Parecki, A., Richer, J., & Hunt, P. (2025). *OAuth 2.0 protected resource
metadata* (RFC 9728). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9728
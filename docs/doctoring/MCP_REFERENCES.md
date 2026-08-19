# MCP standards references

This bibliography supports ADR 0090 and the authenticated LineageWeave MCP resource server. Product claims are pinned to the current MCP revision or the referenced RFC rather than remembered protocol behavior.

## Product decision crosswalk

| Product decision | Source |
|---|---|
| Stateless core, no `initialize`, optional `server/discover` | MCP 2026-07-28 specification release |
| Per-request `_meta`, server identity, `resultType` | MCP 2026-07-28 SDK migration guidance |
| Required `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name` headers | MCP 2026-07-28 Streamable HTTP specification |
| Cache hints on `tools/list` | MCP 2026-07-28 specification release |
| OAuth issuer hardening and DCR deprecation direction | MCP 2026-07-28 authorization changes; RFC 9207 |
| Protected-resource metadata and `WWW-Authenticate` discovery | RFC 9728 |
| Resource-bound access-token audience | RFC 8707 |
| Authorization-server discovery metadata | RFC 8414 |
| Codex MCP OAuth credentials may be stored in an OS keyring | OpenAI Codex operational security guidance |

## APA 7th references

Campbell, B., Bradley, J., & Tschofenig, H. (2020). *Resource indicators for OAuth 2.0* (RFC 8707). Internet Engineering Task Force. https://doi.org/10.17487/RFC8707

Jones, M. B., Hunt, P., & Parecki, A. (2025). *OAuth 2.0 protected resource metadata* (RFC 9728). Internet Engineering Task Force. https://doi.org/10.17487/RFC9728

Jones, M., Sakimura, N., & Bradley, J. (2018). *OAuth 2.0 authorization server metadata* (RFC 8414). Internet Engineering Task Force. https://doi.org/10.17487/RFC8414

Jones, M., Bradley, J., & Sakimura, N. (2022). *OAuth 2.0 authorization server issuer identification* (RFC 9207). Internet Engineering Task Force. https://doi.org/10.17487/RFC9207

Model Context Protocol. (2026, July 28). *The 2026-07-28 specification*. Model Context Protocol Blog. https://blog.modelcontextprotocol.io/posts/2026-07-28/

Model Context Protocol. (2026). *Streamable HTTP: Protocol revision 2026-07-28*. https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/streamable-http.mdx

Model Context Protocol. (2026). *Supporting protocol revision 2026-07-28*. MCP TypeScript SDK. https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28

OpenAI. (2026). *Running Codex safely at OpenAI*. https://openai.com/index/running-codex-safely/

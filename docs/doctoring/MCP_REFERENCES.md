# MCP standards references

This bibliography supports ADR 0090 and the authenticated LineageWeave MCP resource server. Product claims must be traceable to the exact protocol revision or RFC below rather than to remembered MCP behavior.

## Product decision crosswalk

| Product decision | Source |
|---|---|
| MCP protocol revision, JSON-RPC lifecycle | Model Context Protocol 2025-06-18 base protocol |
| Streamable HTTP `/mcp`, POST/GET contract, Origin validation | Model Context Protocol 2025-06-18 transport specification |
| `tools/list`, `tools/call`, structured output, tool annotations | Model Context Protocol 2025-06-18 tools specification |
| MCP HTTP server as OAuth resource server | Model Context Protocol 2025-06-18 authorization specification |
| Protected-resource metadata and `WWW-Authenticate` discovery | RFC 9728 |
| Resource-bound token request/audience | RFC 8707 |
| Authorization-server discovery metadata | RFC 8414 |
| Codex may store MCP OAuth credentials in an OS keyring | OpenAI Codex operational security guidance |

## APA 7th references

Campbell, B., Bradley, J., & Tschofenig, H. (2020). *Resource indicators for OAuth 2.0* (RFC 8707). Internet Engineering Task Force. https://doi.org/10.17487/RFC8707

Jones, M. B., Hunt, P., & Parecki, A. (2025). *OAuth 2.0 protected resource metadata* (RFC 9728). Internet Engineering Task Force. https://doi.org/10.17487/RFC9728

Jones, M., Sakimura, N., & Bradley, J. (2018). *OAuth 2.0 authorization server metadata* (RFC 8414). Internet Engineering Task Force. https://doi.org/10.17487/RFC8414

Model Context Protocol. (2025, June 18). *Authorization*. https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization

Model Context Protocol. (2025, June 18). *Base protocol overview*. https://modelcontextprotocol.io/specification/2025-06-18/basic

Model Context Protocol. (2025, June 18). *Tools*. https://modelcontextprotocol.io/specification/2025-06-18/server/tools

Model Context Protocol. (2025, June 18). *Transports*. https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

OpenAI. (2026). *Running Codex safely at OpenAI*. https://openai.com/index/running-codex-safely/

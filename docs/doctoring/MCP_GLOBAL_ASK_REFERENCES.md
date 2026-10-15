# MCP Global Ask standards register

Supporting research for [ADR 0218](../adr/0218-current-contract-mcp-global-ask.md)
and its current-protocol amendment
[ADR 0272](../adr/0272-stateless-mcp-protocol-dual-era.md). The ADRs are
normative; this register records why each external standard is in scope.

| Source | Adopted contract |
|---|---|
| MCP Streamable HTTP 2025-06-18 | Validate every present Origin, authenticate remote connections, and carry each JSON-RPC message in a new POST request. |
| MCP 2026-07-28 | Serve the stateless revision from the same SDK app: self-describing requests, optional `server/discover`, and `Mcp-Method` / `Mcp-Name` routing headers with fail-closed mismatch. |
| RFC 9728 | Publish protected-resource metadata at the resource-derived well-known location and keep the advertised resource identifier exact. |
| RFC 8707 | Bind the Keyverse access token audience to the MCP resource identifier. |
| RFC 9700 | Apply current OAuth security best practice rather than treating bearer possession as cross-resource authority. |

## References — APA 7th

Campbell, B., Bradley, J., & Tschofenig, H. (2020). *Resource indicators for
OAuth 2.0* (RFC 8707). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8707

Jones, M., Hunt, P., & Parecki, A. (2025). *OAuth 2.0 protected resource
metadata* (RFC 9728). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9728

Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). *Best current
practice for OAuth 2.0 security* (RFC 9700). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9700

Model Context Protocol. (2025). *Transports: Streamable HTTP* (Specification
2025-06-18).
https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

Model Context Protocol. (2026, July 28). *The 2026-07-28 specification*.
https://blog.modelcontextprotocol.io/posts/2026-07-28/

Model Context Protocol Python SDK. (2026). *What's new in v2: The protocol:
2025-11-25 to 2026-07-28*.
https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md


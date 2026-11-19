# Orchestrator client token has no public default

Backend and MCP no longer fall back to the public development token that the
orchestrator rejects. Without a configured internal token the LLM channels are
unavailable instead of failing authentication on every call.

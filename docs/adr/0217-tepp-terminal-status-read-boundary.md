# ADR 0217 — Read TEPP status without treating transport as measurement

**Decision status:** Accepted on this branch; not protected-main truth until merge  
**Date:** 2026-08-26  
**Depends on:** ADR 0022; issue #277; ContextualWisdomLab/TEPP PR #157

## Context

TEPP now publishes a versioned status/read contract for accepted, running,
succeeded, and failed analysis runs. LineageWeave can submit a request but its
client has no read operation, so issue #277 cannot poll a remote run without
bypassing the existing provider boundary.

## Decision

TeppClient.get_analysis_run_status reads one opaque remote run identity
through a separately injected status transport. TEPP PR #157 publishes wire
types but no executable HTTP status route. The configured HTTP client therefore
keeps status reads unavailable instead of deriving an item URL from the submit
collection URL. A later owning-repository route contract may inject a transport
without changing or locally interpreting the opaque identity.

The method returns the unmodified status envelope. This slice does not poll,
persist, validate a terminal digest, append Succeeded, or interpret any
accepted/running envelope as measurement. Those lifecycle operations remain
issue #277 work and must bind the terminal result to the persisted request and
accepted receipt in one transaction.

## Consequences

The later durable worker can reuse the same client instead of introducing a
second client abstraction. Missing transport and malformed identity cannot
manufacture a result; route construction remains unavailable until TEPP owns
and publishes it.

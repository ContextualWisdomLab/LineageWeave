# ADR 0125: Use a vetted AEAD for ontology source cursors

**Status:** Accepted
**Date:** 2026-08-21
**Issue:** PR #349 review finding on the custom cursor keystream
**Predecessor:** [ADR 0124](0124-ontology-source-window-cursor.md)

## Context

The ontology continuation cursor is an authenticated, short-lived bearer
token. Its claims include SQL ordering keys and authorization-bound snapshot
digests, so confidentiality and tamper detection are both required. The
previous `src.v1.` implementation combined an HMAC-derived keystream with a
separate HMAC tag. A bespoke encryption construction is harder to audit than a
vetted authenticated-encryption primitive.

## Decision

1. Mint `src.v2.` cursors with `cryptography`'s AES-GCM implementation.
2. Use a fresh 96-bit nonce per token and bind the prefix/version as associated
   data. Derive the 256-bit AES key from the process secret with a
   domain-separated HMAC-SHA256 derivation.
3. Reject v1 and malformed, tampered, expired, scope-mismatched, or stale
   tokens with the existing fail-closed `malformed_cursor`/`stale_snapshot`
   errors. No migration is needed because the maximum cursor lifetime is 15
   minutes.
4. Keep the minimum process secret length and never place account, tenant, or
   hidden endpoint identifiers in plaintext.

## Consequences

The implementation removes custom `_keystream`/`_xor` encryption code and
delegates authenticated encryption to a maintained library. Existing v1
cursors expire naturally and are rejected during the rollout; clients request
the first page again.

## References

Dworkin, M. (2007). *Recommendation for block cipher modes of operation:
Galois/Counter Mode (GCM) and GMAC* (NIST Special Publication 800-38D).
National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-38D

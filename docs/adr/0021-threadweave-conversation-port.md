# ADR 0021 — Fail-closed ThreadWeave conversation port

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

LineageWeave already calls ThreadWeave inside `reconstruct.py` to
assemble RankWeave parent choices into trees. Demo Analyst had no
buyer-facing Conversations surface over those persisted edges.
ThreadWeave is an in-process library
([API contract](https://github.com/ContextualWisdomLab/ThreadWeave/blob/main/docs/API_CONTRACT.md)):
it does not define HTTP, a mailbox host, or authentication. A missing
package, a disabled port, or a JWZ dummy for a hidden parent must not
become an invented conversation.

This ADR does not replace `reconstruct.py`, does not read naruon
tables, and does not bind the demo IdP to production Keyverse. ADR
0020 already reserved later mapping of mailbox threads onto lineage
posts; this slice threads *visible* `source_post` rows only.

## Decision

1. Consume ThreadWeave only through `ThreadWeaveClient`. The default
   transport raises `ThreadWeaveNotAvailable`. `build_threadweave_client
   (disabled=False)` uses `LibraryThreadWeaveTransport`, which imports
   `thread_messages` inside the call so a missing package fail-closes.
2. `GET /api/conversations` (`post_read`) loads ABAC-visible posts and
   visible-only `post_lineage_edge` rows as JWZ `references`. A hidden
   parent is omitted; the child becomes a root. Never invent a parent.
3. Dummy JWZ containers (referenced-but-missing ids) lift their
   children instead of projecting an untitled parent.
4. After login, Conversations sits above Calendar. Unavailable copy is
   **Conversations · ThreadWeave not available**. An accepted tree
   lists the root title; click opens that `source_post`.

## Consequences

`THREADWEAVE_DISABLED=1` keeps the fail-closed transport. The default
seeded stack uses the in-process library and lists the designed A-100
fork when those posts are visible. Mailbox stays on ADR 0020 / #217.
Leftover pairs stay on #211. TEPP stays on #214.

## References

Crispin, M., & Murchison, K. (2008). *Internet Message Access Protocol
— SORT and THREAD extensions* (RFC 5256). IETF.
https://doi.org/10.17487/RFC5256

Zawinski, J. (2002). *Message threading* [Technical note].
https://www.jwz.org/doc/threading.html

Contextual Wisdom Lab. (2026). *ThreadWeave public API and version
contract* [Software documentation].
https://github.com/ContextualWisdomLab/ThreadWeave/blob/main/docs/API_CONTRACT.md

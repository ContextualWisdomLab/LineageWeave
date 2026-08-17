# ADR 0020 — Fail-closed naruon mailbox port

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

LineageWeave reconstructs lineage from records that already exist
somewhere else. The org mailbox control plane is
[naruon](https://github.com/ContextualWisdomLab/naruon). naruon is not
an SMTP/IMAP host; it exposes a signed inbox envelope at
`GET /api/emails`. Until this slice, Demo Analyst had no mailbox
surface: a down naruon port was silent, and nothing stopped a later
writer from inventing a "Quarterly plan" thread.

TEPP already owns the naruon→TEPP analysis-run interchange
(`docs/connectors/naruon-artifact-consumer.md` in TEPP). This ADR does
not reimplement that interchange, invent a second analysis-run
registry, or bind the demo IdP to production Keyverse.

## Decision

1. Consume naruon only through `NaruonClient` and the published
   `GET /api/emails` envelope. Never read naruon tables.
2. The default transport raises `NaruonNotAvailable`. HTTP 4xx/5xx,
   timeout, network, non-https, and an unknown envelope fail closed.
3. Project `thread_id`, `subject`, and optional `reply_count` only.
   Message bodies, raw ids, and provider credentials are not copied.
4. `GET /api/mailbox` (post_read) returns `unavailable` +
   `naruon_not_available` + empty `threads` when the port is down.
   Seed probes the same client and never inserts an invented email.
5. After login, the home Mailbox panel names that status. An accepted
   thread lists its subject; click does not invent a `source_post`.

## Consequences

Demo Analyst sees **Mailbox · naruon not available** after `make seed`
when `NARUON_BASE_URL` is empty. A live naruon transport can list the
published Quarterly plan fixture without fabricating a post. Later
mapping of mailbox threads onto lineage posts is a separate slice.

## References

Contextual Wisdom Lab. (2026). *Naruon AI email workspace* [Software
documentation]. https://github.com/ContextualWisdomLab/naruon

Contextual Wisdom Lab. (2026). *naruon artifact consumer* [Connector
contract]. https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/connectors/naruon-artifact-consumer.md

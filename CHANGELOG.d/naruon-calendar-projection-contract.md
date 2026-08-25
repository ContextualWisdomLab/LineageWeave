# Naruon calendar projection contract

## Added

- Add a strict, bounded v1 consumer contract for calendar occurrences already authorized and policy-filtered by Naruon, including occurrence identity, provider revision, timezone/all-day semantics, disclosure level, and observed provenance.
- Export the projection parser, immutable result types, media type, schema version, and read client through the public LineageWeave package surface.
- Add a reusable bounded JSON response read so oversized pages are rejected before allocation and parsing.

## Changed

- Clarify that LineageWeave owns post-grounded commitments and issue/todo records, while Naruon owns provider CalDAV synchronization, revisions, writeback, retry, and reconciliation.
- Replace the misleading CalDAV label on the earlier custom JSON `/events` feed with an explicit pseudo-CalDAV correction.

## Security

- Reject unsafe base URLs, whitespace/control-bearing service tokens, unbounded response bodies, invalid numeric controls, oversized pages/windows, naive timestamps, duplicate occurrences, unknown fields/vocabularies, and URL-shaped opaque references.

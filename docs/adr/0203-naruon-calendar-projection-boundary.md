# ADR 0203: Consume calendar observations through Naruon

- Status: Accepted
- Date: 2026-08-21
- Issue: #336
- Related authority: `ContextualWisdomLab/naruon#978`, `#998`, and `#1437`

## Context

LineageWeave derives customer commitments from authorized post evidence and
stores them as issue tickets with due dates. The Buyer Calendar can therefore
show two different kinds of records:

1. LineageWeave-authoritative commitments and To Do records; and
2. external calendar events observed in a customer-owned provider.

ADR 0038 correctly separated these collections but named a custom JSON
`GET {CALDAV_BASE_URL}/events` feed as CalDAV. That endpoint does not implement
RFC 4791 discovery, WebDAV REPORT, iCalendar recurrence or VTIMEZONE, RFC 6578
synchronization, ETag reconciliation, scheduling, or provider authorization.
The name therefore overstates the shipped product.

Naruon is the CWL authority for customer-owned mail, calendar, contact, and file
provider interaction. Its scheduling boundary owns typed event/commitment
semantics, DAV capability discovery, synchronization, provider revisions,
writeback, retries, and reconciliation. Reimplementing those responsibilities
inside LineageWeave would duplicate credentials and provider state and would
turn LineageWeave into a second calendar product.

## Decision

LineageWeave consumes a **read-only, versioned Naruon calendar projection**. It
does not connect to a CalDAV provider directly.

The contract is implemented by:

- `lineageweave.naruon_calendar_projection`;
- `docs/contracts/naruon-calendar-projection-v1.schema.json`; and
- strict parser, transport, byte-bound, and public-package tests in
  `tests/test_naruon_calendar_projection.py` and `tests/test_http_client.py`.

The projection endpoint is conceptually:

```text
GET {Naruon base}/api/calendar/events
  ?window_start=<RFC3339>
  &window_end=<RFC3339>
  &limit=<1..200>
  [&cursor=<opaque>]
```

The request uses an audience-scoped service credential configured for the
LineageWeave deployment. It does not forward a browser or end-user bearer token,
and it never receives provider credentials. The credential must be a bounded
single token without whitespace or control characters. The consumer admits at
most a 1 MiB response body before JSON parsing.

Each occurrence carries only:

```text
event_reference
occurrence_reference
source_reference
provider_revision
display_text
starts_at
ends_at
all_day
time_zone
status_code
disclosure_code
truth_status_code = observed
observed_at
```

Naruon applies tenant, source, participant, and disclosure policy before the
response crosses the service boundary. `busy_only` rows contain only safe
Naruon-supplied display text. Attendees, descriptions, provider URLs, private
conflict reasons, access tokens, and raw DAV payloads are outside this contract.

LineageWeave keeps the two truth domains separate:

```text
LineageWeave commitment
- authoritative post-derived work record
- issue/todo identity
- source-post evidence and ontology/provenance

Naruon event projection
- observed provider occurrence
- opaque Naruon source/event/occurrence identity
- provider revision and observation time
```

An observed external event is never promoted into an internal commitment merely
because it appears in the same Calendar screen.

## Validation and failure posture

The LineageWeave consumer rejects:

- non-HTTP(S), userinfo-bearing, query-bearing, fragment-bearing, whitespace, or
  control-bearing base URLs;
- missing, control-bearing, or whitespace-bearing service credentials;
- windows longer than 366 days;
- pages larger than 200 events or response bodies larger than 1 MiB;
- unknown fields, schema versions, status, disclosure, or truth vocabularies;
- naive timestamps, invalid intervals, and duplicate occurrence references;
- URL-shaped or whitespace-bearing opaque references and cursors;
- boolean, fractional, or out-of-range page limits and invalid timeouts.

The adapter follows no redirects through the current shared HTTP client. Errors
identify the configured host when necessary but never include the service
credential or response body.

Until Naruon ships the matching read endpoint and service-audience contract,
LineageWeave runtime wiring remains disabled and fail-closed. Existing internal
commitments remain available even when the external event channel is absent.

LineageWeave v2.17.0 implements activation gate step 2: `GET /api/calendar`
and the 달력 destination consume `NARUON_CALENDAR_BASE_URL` /
`NARUON_CALENDAR_SERVICE_TOKEN` through
`lineageweave.naruon_calendar_workspace`. A missing audience, malformed
token, transport failure, or contract rejection returns `events: []` with
`naruon_available: false` and never invents an occurrence. Steps 3–5
(provider/consumer fixtures against a released Naruon artifact, degraded
behavior, and protected merge) remain open. Do not treat this wiring as a
completed Naruon connector.

## Consequences

### Positive

- Product language no longer implies CalDAV interoperability that does not
  exist.
- Provider credentials, sync cursors, ETags, recurrence reconciliation, and
  scheduling remain in one authority.
- LineageWeave gains a strict, bounded ontology/provenance-compatible event
  observation contract without creating another event store.
- Calendar commitments and external observations remain auditable and cannot be
  silently conflated.
- The contract may merge and be released independently while runtime activation
  remains disabled.

### Costs and limitations

- The Buyer Calendar will not show external events until Naruon implements and
  releases the corresponding read projection.
- The two repositories require provider/consumer contract tests before runtime
  activation.
- This decision does not claim provider interoperability, CalDAV conformance, or
  a completed Naruon connector.
- Contract v1 does not include attendees, recurrence rules, or provider URLs;
  broader disclosure requires a new reviewed contract version.

## Runtime activation gate

Runtime activation requires all of the following:

1. Naruon publishes the matching endpoint, media type, service audience, and
   conformance fixtures;
2. LineageWeave wires configuration and the Buyer API without forwarding an
   end-user token;
3. provider/consumer fixtures pass against immutable released artifacts;
4. degraded, timeout, retry, revision, and reconciliation behavior is tested;
5. exact-head security, coverage, review, and protected merge gates pass in both
   repositories.

## References

See `docs/doctoring/NARUON_CALENDAR_PROJECTION_REFERENCES.md`.

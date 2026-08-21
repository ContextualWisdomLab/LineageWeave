# ADR 0112: Bind summary events to source-grounded projects

- Status: Accepted
- Date: 2026-08-20

## Decision

Summary events retain their buyer-facing text but may carry a normalized
`project_key` that must reference the same post's `post_project_mention` row.
The API exposes the resolved project name in `key_event_details`; the legacy
`key_events` string list remains for clients that have not adopted the detail
field. Unsupported or ambiguous project bindings remain `NULL` rather than
being inferred from customer, PU, sales-pool, author, or title hints.

## Rationale

A post may describe several unrelated projects. A single unscoped event list
loses which project a decision belongs to, which makes the Board, Ask Agent,
and lineage navigation unsafe. The composite foreign key keeps the event
projection normalized and source-grounded.

## Consequences

LLM responses may propose a project key, but persistence validates it against
the post's explicit or semantically supported project mentions. Existing
clients continue to render `key_events`; updated clients can show project
labels without exposing internal keys.

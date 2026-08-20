# ADR 0111: Bind major event actions to source-grounded projects

- Status: Accepted
- Date: 2026-08-20

## Context

One post can describe more than one project or matter. The existing semantic
summary persisted project mentions and major event actions separately, so the
Buyer popup could display a correct-looking action list while losing which
project each action belonged to. A later summary consumer then had no safe way
to separate projects without guessing from action text.

## Decision

1. Extend `MajorEventAction` with an optional normalized `project_key`.
2. Require contextual-orchestrator to emit the project canonical key for an
   action only when it exactly matches a project in the same semantic response;
   legacy four-column/plain and JSON responses remain parseable with no key.
3. Persist the association in `post_summary_action.project_key` with a
   composite foreign key to `post_project_mention(post_id, project_key)`.
4. When persisting, discard an unsupported association rather than binding an
   action to a guessed project. The action remains source-grounded and may be
   shown without a project.
5. Read the buyer-facing project name through the normalized project mention
   join. Never expose the internal project key, ontology IRI, or orchestrator
   identifier in the UI.

This extends ADR 0036's multi-project evidence rule and ADR 0052's
orchestrator-only semantic boundary. It does not create a new event ontology
or infer project membership from title, customer, PU, sales-pool, or author
hints.

## Consequences

Project-specific actions can be separated in the post view and remain
referentially valid after re-ingestion. Unassigned actions are explicit
source events without a fabricated project assignment. Existing persisted
actions remain compatible because the new column is nullable.

## Verification

- Parser tests cover the new five-column plain response and legacy JSON shape.
- The migration test verifies the composite foreign key target.
- Runtime LLM evaluation remains subject to the contextual-orchestrator test
  environment and uses only synthetic repository fixtures.

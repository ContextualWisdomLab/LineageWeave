# ADR 0044: Source Author Account Context for Keyman Hints

## Status

Accepted

## Context

Imported posts carry a source author code, while the existing row also has an
authenticated `author_account_id`. The account's existing `account_affiliation`
rows and process-unit association are useful priors for deciding whether a
person named in the body is on our side. Dropping that context whenever a
source field exists prevents Keyman extraction from using one of the strongest
available side hints. Treating it as an identity match would be unsafe: the
account is an authorization subject, not proof that a named person is the
same cataloged Keyman.

## Decision

- Retain `source_post.author_account_id`, `user_account.display_name`, and
  authorized `account_affiliation` entity/process-unit labels as explicit
  source context for Keyman extraction.
- Expose the same context from the customer-master and post Keyman contracts
  with `resolution_status=our_side_context_only` when an authorized affiliation
  exists; otherwise keep it `source_author_hint_only`.
- Keep source author code/name and account context as hints with provenance;
  never create, merge, or bind a `cataloged_person` from those fields alone.
- The contextual-orchestrator prompt may use the account context as a prior,
  but a person's textual name, role, or affiliation must still support a
  Keyman mention.
- Limit account affiliations returned to the requesting account's authorized
  corporate-entity scope. Preserve the distinction that process-unit codes are
  PU/business-unit context, not sales-pool identity.

## Consequences

Keyman extraction can distinguish our-side candidates using existing account
context without inventing a person identity. Buyers can inspect the provenance
of the hint, while unresolved names remain unresolved until text-backed
semantic evidence exists.

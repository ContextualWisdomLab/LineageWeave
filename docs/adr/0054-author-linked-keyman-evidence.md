# ADR 0054: Author-linked Keyman evidence

## Status

Accepted

## Context

The source author is an important prior for finding our-side Keymen, but an
author code or display name is not a person identity. A customer-master view
that exposes only the author account loses persisted semantic evidence already
recorded for the same visible posts.

## Decision

- For each authorized source-author hint, expose `keyman_hints` only from
  `post_summary_role.cataloged_person_id` joined to `cataloged_person`.
- Keep only `actor_type_code=prov_person` and `person_side_code=our_side`.
- Include the catalog id, name, side, optional job title, visible-post mention
  count, and a fixed provenance value; never rejoin by display name.
- Treat the result as a buyer-facing hint. It does not bind the source author
  to the cataloged person, create a person, or replace post-level evidence.
- Keep the existing ABAC-filtered source-post scope and related body excerpts.

## Consequences

Customer master can use our-side author context to surface likely Keymen while
preserving the distinction between an authorization subject, a semantic
mention, and a catalog identity. Unresolved authors remain unresolved.

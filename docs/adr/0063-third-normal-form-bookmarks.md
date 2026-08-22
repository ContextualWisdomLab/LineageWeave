# ADR 0063: Store Buyer bookmarks in a third-normal-form relation

- Status: Accepted
- Date: 2026-08-19

## Context

The post detail popup needs a durable Bookmark action. A bookmark is an
account-owned domain record, not source evidence and not a UI-only flag. Using
`(user_account_id, post_id)` as the bookmark table's primary key would encode
the relationship directly as the identity of the domain record and prevent a
stable bookmark reference for later activity, auditing, or additional bookmark
attributes.

## Decision

Use a `post_bookmark` table with:

- `bookmark_id` as the independent surrogate primary key;
- `user_account_id` as a foreign key to `user_account`;
- `post_id` as a foreign key to `source_post`;
- bookmark lifecycle timestamps as attributes of the bookmark row;
- a separate unique alternate constraint on `(user_account_id, post_id)` to
  enforce one active bookmark per account and post.

The composite account/post pair is therefore a business invariant only, never
the primary identity of the bookmark entity. No display name, post title, or
authorization scope is duplicated in `post_bookmark`; those values remain in their
normalized source tables. Every read and write still performs the normal
visible-post ABAC check for the requesting account.

The historical migration introduced this entity as `bookmark`; ADR 0120
renames the persistent relation to `post_bookmark` to enforce the repository's
two-word database-identifier rule. The entity and authorization decision stay
unchanged.

## Consequences

- A bookmark has a stable identifier and remains in third normal form: every
  non-key attribute depends on the bookmark identifier, the whole identifier,
  and nothing but the identifier.
- Account isolation and post deletion remain database-enforced through foreign
  keys and cascades.
- The unique alternate constraint prevents duplicate user actions without
  making the relationship pair the entity primary key.

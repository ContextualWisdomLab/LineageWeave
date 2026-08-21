# ADR 0122: Ticket mutation requires owning-post authorization

- Status: Accepted
- Date: 2026-08-21

## Context

An `issue_ticket` has no independent visibility policy; it inherits the
visibility of its owning `source_post`. That inheritance is sufficient for a
read, but a `post_admin` account must not turn public read access into a write
right over another account's workflow ticket. The old PATCH path checked the
permission and post visibility, then mutated the child row without checking the
authoring boundary.

## Decision

Ticket create and update require all of the following:

1. `post_admin` permission;
2. visibility of the owning post under the normal ABAC predicate; and
3. either authorship of the owning post or affiliation with its corporate
   entity.

The check is performed after resolving the ticket's owning post and before
the ticket mutation. Public visibility remains a read property and does not
grant cross-account ticket mutation. Unknown ticket identifiers still return
404 before any authorization detail is disclosed.

## Consequences

- A public post can be read without exposing its ticket workflow to unrelated
  administrators.
- Private same-corporate ticket management remains unchanged.
- Future child resources must resolve and enforce the owning-post write
  boundary instead of copying a visibility check.

## References — APA 7th

National Institute of Standards and Technology. (2020). *Security and privacy
controls for information systems and organizations* (NIST Special Publication
800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5

OWASP Foundation. (2025). *Authorization testing guide*. OWASP Web Security
Testing Guide. https://owasp.org/www-project-web-security-testing-guide/

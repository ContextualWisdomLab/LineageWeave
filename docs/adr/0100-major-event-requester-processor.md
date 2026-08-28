# ADR 0100 — Major event actions retain requester and processor evidence

**Decision status:** Accepted
**Date:** 2026-08-20
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Figma File URL:** https://www.figma.com/design/1Su3lDRmiZdcUs47t1QwIX

## Context

The summary popup already showed major events and role/responsibility rows,
but it did not answer the operational question that follows those facts:
who requested each event and who must process it. Copying those names into a
new denormalized row would duplicate actors and lose the existing catalog
links.

## Decision

1. The contextual-orchestrator semantic summary contract adds
   `major_event_actions`. Each action contains an event/action statement, an
   optional requester actor name, an optional processor actor name, and a
   source evidence phrase.
2. Requester and processor names are nullable when the source does not name
   them. The system never invents `미상` or a viewer/account identity.
3. Persist actions in `post_summary_action`, keyed by `(post_id,
   action_ordinal)`. Both actor names are composite foreign keys to the
   existing `(post_id, actor_name)` `post_summary_role` key. This keeps the
   action fact, actor identity, and catalog binding in third normal form.
4. Increment the summary contract version from 4 to 5. Existing summaries
   are stale until regenerated from the source post.
5. The popup renders the action, requester, processor, and evidence directly
   below the existing R&R list. It reuses the current popup and design-token
   boundary; no new Figma file is required.

## Consequences

- Buyer-facing summaries expose an actionable handoff instead of only a
  descriptive role list.
- Actions with an actor name that is not present in the same summary's role
  projection are dropped rather than persisted with an unbound name.
- A provider response without an action is valid when the source contains no
  explicit request or processing assignment; absence remains missing
  evidence, not a guessed assignment.

## Related

- [ADR 0006](0006-role-responsibility-agent-ontology.md)
- [ADR 0052](0052-plain-orchestrator-semantic-evidence.md)
- [ADR 0076](0076-paper-grounded-model-policy.md)
- W3C. (2013). *PROV-O: The PROV ontology*. https://www.w3.org/TR/prov-o/

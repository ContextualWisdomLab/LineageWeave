# ADR 0235: Persisted per-post Ask conversation history

* Status: Accepted
* Date: 2026-08-23
* Figma: File ID `1Su3lDRmiZdcUs47t1QwIX`
* Related: [0090](0090-global-ask-lineage-timeline-expansion.md), [0118](0118-uiux-standard-guide-v3-design-overhaul.md)

## Context

The post popup **Ask about this lineage** surface stored one shared
`post_chat_result` row per
`(post_id, question_norm)` and rendered a linear transcript plus re-ask
chips. Leaving the popup, switching questions, or starting a new thread
could not reopen an earlier account-owned conversation on that post.

That is a different metaphor from the conversation-history sidebar the
reader already uses on Ask Agent. Seeded fixture answers remain the
orchestrator-off demo cache; they are not a substitute for account-owned
history.

## Decision

Persist per-post Ask conversations under the authenticated `user_account`
and the visible `source_post`: an explicit
conversation id, list/select/new, and visibility-filtered citations on
read. Do not represent this id as a Global Ask session id or as a fake
post-scoped orchestrator session id.

Normalized tables:

* `post_ask_session` — multiple conversations may belong to the same account
  and post
* `post_ask_turn` — ordered questions and answers
* `post_ask_turn_citation` / `post_ask_turn_source` — cited and retrieved
  posts

The composite index `(user_account_id, post_id, updated_at desc)` leads
with the account so a hot post cannot concentrate list traffic on one
partition key. A turn is written only after a complete answer exists
(seeded cache hit or orchestrator object). History reads re-apply current
post visibility before returning titles or citations.

`post_chat_result` stays the post-level seeded/cache store used when the
orchestrator is off. Account history is additional, not a replacement.

## Consequences

* A reader can list saved questions on a post, reopen one and see its
  turns, and start a new conversation without losing the list.
* A user cannot read another account's post conversation by changing a
  UUID, and cannot load a conversation against a different post id.
* Revoked post visibility removes that post's citation projection; the
  stored answer remains account-owned transcript data.
* TEPP topic modeling of how many posts can connect, and how many
  lineages form under temporal precedence, remains deferred.
* Reauthorization for a conversation's turns is batched
  (`_visible_post_ids_batch`, one query per relation type per page instead
  of per turn), preventing transcript length from creating an N+1 query path.
* `persist_turn` now row-share-locks and re-authorizes every
  `source_post_id` inside its own commit transaction
  (`_ensure_sources_visible`, raising `PostAskEvidenceChanged` -> 503).
  Persisted citations remain a subset of those authorized sources, so a
  cited or non-cited source that loses authorization between source-gathering
  and commit aborts the whole turn.

## Implementation Plan

* **Affected paths:** `migrations/0223_post_ask_conversation_history.sql`,
  `backend/app/post_ask_history.py`, `backend/app/main.py`,
  `frontend/src/api.ts`, `frontend/src/App.tsx` (`ChatPanel`),
  `frontend/src/i18n.ts`, `tests/test_post_ask_history.py`,
  `frontend/src/ChatPanel.test.tsx`
* **Pattern:** require `post_id` and `user_account_id` scope on every query.
* **Verification:** backend tests drive `list_conversations`,
  `fetch_conversation`, and `persist_turn`. Frontend tests click New
  conversation, select a saved conversation, and assert the matching turns.

## References — APA 7th

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

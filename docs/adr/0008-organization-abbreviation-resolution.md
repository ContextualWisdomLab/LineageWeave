# ADR 0008 — Abbreviated organization names are resolved and search-verified, not left opaque

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

Real post text names organizations by abbreviated or slang forms a
human reader immediately recognizes but a string-matching pipeline
cannot -- e.g. "AGP," a common Korean contraction of "Aurora Grid Power"
(Korea Hydro & Nuclear Power). `lineageweave.corporate_hierarchy_resolution`
already resolves near-matches (a trailing legal suffix, a minor
abbreviation) via character-sequence similarity
(`difflib.SequenceMatcher`, grounded in Bhattacharya & Getoor, 2007's
candidate-generation stage), but an initialism/contraction like "AGP"
shares almost no character substring with its expansion -- no
similarity threshold recovers it, because the two strings are not
similar, they are *related by real-world knowledge* the text or an
external source has to supply.

Left unresolved, every mention of the same real organization under its
abbreviated name creates its own unmatched, un-linkable free-text
string in `person_affiliation`/R&R -- the same organization looks like
N different unknown entities across N posts, each failing to link into
the corporate hierarchy a human reader would recognize instantly.

## Decision

A two-stage pipeline, reusing infrastructure this repo already has for
a structurally identical problem (ADR: `lineageweave.relation_verification`,
FEVER-style claim verification) rather than building a second web-search
integration:

1. **LLM context resolution**
   (`lineageweave.organization_name_resolution.ContextualOrchestratorOrganizationNameResolutionClient`):
   given the raw abbreviated name and the post's own text as context,
   ask the model for the organization's full real-world name, or
   `UNKNOWN` when the text gives no real basis to determine one --
   never inventing an expansion from the abbreviation's letters alone.
2. **External search cross-verification**
   (reusing `lineageweave.relation_verification.RelationVerificationClient`
   as-is, not a new client class): the proposed full name plus the raw
   abbreviation together become the search query (e.g. "Aurora Grid Power
   AGP") -- a real page mentioning both together is strong
   corroboration the specific pairing is correct, not just that the
   full name exists as *some* organization.

Grounded in SKOS (Miles & Bechhofer, 2009): `skos:prefLabel` (a
resource's one preferred/canonical label) and `skos:altLabel` (an
alternative label -- exactly the abbreviation/synonym relationship) is
the standard vocabulary for a raw-name/canonical-name pair. This is a
different, complementary standard from ADR 0006/0007's PROV-O/ORG
classes: SKOS here labels the *string identity* relationship between
two names for the same thing, not the *type* of the named actor.

Only a search-corroborated resolution is ever substituted in for
downstream entity matching (`resolve_corporate_entity`) -- an
LLM-proposed name with no corroboration, or with verification itself
unavailable, leaves the raw name flowing unchanged. This is the same
never-trust-an-unverified-guess discipline `relation_verification`
itself already established: a wrong resolution corrupts every
downstream Knowledge Graph link through it, so "did not resolve" must
stay a real, distinguishable outcome from "resolved to X."

Persistence: a new `organization_name_resolution` cache table
(`migrations/0015_organization_name_resolution.sql`), keyed by
`raw_organization_name` -- the same abbreviation is resolved once, not
re-queried on every one of its (potentially many) mentions across
posts. `verification_status_code` reuses the existing
`relation_verification_status` lookup category rather than a
near-duplicate one: a resolved name is corroborated/uncorroborated the
exact same way a classified relationship already is.

Wired into `backend/app/keyman_ingestion.py`'s affiliation loop (the
concrete case real data surfaced): each affiliated organization name is
resolved before `resolve_corporate_entity` sees it, so a
search-corroborated resolution gets the character-similarity match its
raw abbreviated form never could.

## Consequences

- The raw abbreviated form is not duplicated onto every row that
  mentions it (e.g. `person_affiliation.affiliated_organization_name`
  stores the resolved canonical name once corroborated) -- it remains
  fully recoverable via a join against `organization_name_resolution`,
  which is the authoritative raw-form/canonical-form/evidence record.
  This is 3NF-motivated, not a loss: repeating the raw-to-canonical
  mapping per affiliation row would be the actual redundancy.
- A person_affiliation row's unique key
  (`person_id, affiliated_organization_name`) is on the *stored* name.
  If Searxng availability changes between two extraction runs on the
  same post (first run: unavailable, raw name stored; later run:
  available, resolved name stored), the two runs can leave both the raw
  and resolved variants as separate rows for the same real affiliation,
  rather than cleanly upgrading one row in place. A real, narrow edge
  case (only triggers on a mid-flight verification-availability change
  for the same post+person), not fixed here -- same category of
  near-duplicate-variant risk `resolve_corporate_entity`'s own
  candidate matching already accepts for minor raw-string differences.
- Every channel here follows the existing pluggable-client discipline:
  `NullOrganizationNameResolutionClient`/an unavailable verification
  client degrade to "use the raw name," never a fabricated resolution.
- `extract_post_keymen`'s entity-relationship classification step (the
  same request, right after Keyman extraction) still builds its
  `organization_names` list from each `PersonMention`'s own
  `affiliated_organization_names` -- the raw names the LLM extracted,
  not the resolved names `ingest_post_keymen` just persisted. A real,
  known gap: an abbreviation resolved for the Keyman/affiliation side
  is not yet threaded through to the counterparty-relationship
  classification side of the same request. Not fixed here (it needs
  `ingest_post_keymen` to hand resolved names back to its caller, a
  small but separate change); tracked here rather than silently
  shipped as if both sides already agreed.

## Related

Complements [ADR 0006](0006-role-responsibility-agent-ontology.md) and
[ADR 0007](0007-team-actor-type.md) (actor *type*), and reuses
`lineageweave.relation_verification` (ADR-less, predates this file, see
its own module docstring for FEVER grounding) for the verification
stage rather than duplicating it.

## References (APA 7th)

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, 1(1), Article 5. https://doi.org/10.1145/1217299.1217304

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A large-scale dataset for fact extraction and VERification. In *Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies* (pp. 809–819). Association for Computational Linguistics. https://doi.org/10.18653/v1/N18-1074

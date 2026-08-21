# ADR 0008 — Abbreviated organization names are resolved and search-verified, not left opaque

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

Real post text names organizations by abbreviated or slang forms a
human reader immediately recognizes but a string-matching pipeline
cannot -- e.g. "AGP," a synthetic contraction of "Aurora Grid Power".
`lineageweave.corporate_hierarchy_resolution`
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
The reverse failure is equally unsafe: the same short name can refer to
different organizations in different post contexts, so a context-free cache
can link later mentions to the first model answer by accident.

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

Global Ask treats only search-corroborated rows as a multilingual label
projection. A raw abbreviation, local-language name, or translated name that
has actually appeared in a post context can therefore nominate the same posts
as its canonical corporate-entity name. The projection joins the corroborated
`resolved_organization_name` back to `corporate_entity`; pending and
uncorroborated rows remain invisible. After ABAC-visible posts are selected,
Global Ask discloses the matched raw→canonical pair on cited-post evidence and
names opening Event Lineage as the next action (ADR 0107). It does not generate
translations or infer aliases at query time. This preserves the source-observed
label and the SKOS preferred/alternative-label distinction while applying the
document-level context required by multilingual entity linking (De Cao et al.,
2022).

Only a search-corroborated resolution is ever substituted in for
downstream entity matching (`resolve_corporate_entity`) -- an
LLM-proposed name with no corroboration, or with verification itself
unavailable, leaves the raw name flowing unchanged. This is the same
never-trust-an-unverified-guess discipline `relation_verification`
itself already established: a wrong resolution corrupts every
downstream Knowledge Graph link through it, so "did not resolve" must
stay a real, distinguishable outcome from "resolved to X."

Persistence: the `organization_name_resolution` cache table
(`migrations/0015_organization_name_resolution.sql`, extended by a later
migration that adds `context_sha256`) is keyed by
`raw_organization_name` plus a SHA-256 digest of the bounded post context.
The context body is not persisted in the cache. Exact-context reprocessing
can reuse a result, while a homonymous abbreviation in a different context
gets a separate resolution instead of inheriting the first answer.
`verification_status_code` reuses the existing
`relation_verification_status` lookup category rather than a
near-duplicate one: a resolved name is corroborated/uncorroborated the
exact same way a classified relationship already is.

Wired into `backend/app/keyman_ingestion.py`'s affiliation loop (the
concrete case real data surfaced): each affiliated organization name is
resolved before corporate-entity matching and creation. A corroborated
canonical name is returned to the caller as part of the normalized
`PersonMention`, so the same request's relationship classifier uses the
canonical form too rather than reintroducing the raw abbreviation.

## Consequences

- The raw abbreviated form is not duplicated onto every row that
  mentions it (e.g. `person_affiliation.affiliated_organization_name`
  stores the resolved canonical name once corroborated) -- it remains
  fully recoverable via a join against `organization_name_resolution`,
  which is the authoritative raw-form/canonical-form/evidence record.
  This is 3NF-motivated, not a loss: repeating the raw-to-canonical
  mapping per affiliation row would be the actual redundancy.
- Resolution availability can improve between extraction runs. When a
  prior raw affiliation later resolves, `_upsert_affiliation` promotes
  it transactionally: the canonical row is inserted or updated while
  preserving any previously resolved corporate-entity link and role
  title, and the obsolete raw-name row is deleted when the two names
  differ. This avoids leaving duplicate raw and canonical identities for
  the same person.
- `ingest_post_keymen` returns the normalized mentions it persisted.
  `extract_post_keymen` therefore passes canonical organization names to
  entity-relationship classification and returns those same names on
  the API response; affiliation persistence, relationship classification,
  and the caller-visible payload agree within one transaction.
- Every channel here follows the existing pluggable-client discipline:
  `NullOrganizationNameResolutionClient`/an unavailable verification
  client degrade to "use the raw name," never a fabricated resolution.
- Context-sensitive caching follows entity-linking evidence that ambiguous
  mentions must be disambiguated with document-level semantic context, not a
  name-only lookup (Rama-Maneiro, Vidal, & Lama, 2020).
- Search can cross language and abbreviation boundaries only after the existing
  contextual-orchestrator plus SearXNG evidence path corroborates that label
  pair. An unseen or unverified translation remains unavailable rather than
  becoming a guessed catalog alias.

## Related

Complements [ADR 0006](0006-role-responsibility-agent-ontology.md) and
[ADR 0007](0007-team-actor-type.md) (actor *type*), and reuses
`lineageweave.relation_verification` (ADR-less, predates this file, see
its own module docstring for FEVER grounding) for the verification
stage rather than duplicating it.

## References (APA 7th)

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, 1(1), Article 5. https://doi.org/10.1145/1217299.1217304

De Cao, N., Wu, L., Popat, K., Artetxe, M., Goyal, N., Plekhanov, M., Zettlemoyer, L., & Riedel, S. (2022). Multilingual autoregressive entity linking. *Transactions of the Association for Computational Linguistics, 10*, 274–290. https://doi.org/10.1162/tacl_a_00460

Rama-Maneiro, E., Vidal, J. C., & Lama, M. (2020). Collective disambiguation in entity linking based on topic coherence in semantic graphs. *Knowledge-Based Systems, 199*, Article 105967. https://doi.org/10.1016/j.knosys.2020.105967

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A large-scale dataset for fact extraction and VERification. In *Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies* (pp. 809–819). Association for Computational Linguistics. https://doi.org/10.18653/v1/N18-1074

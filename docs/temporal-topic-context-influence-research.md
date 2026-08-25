# Temporal topic and context-influence evidence brief

## Research question

How can LineageWeave present time-aware, lineage-aware topics and identify the
posts that influence topic estimates at business-unit, PU, team, and person
levels without keyword rules or arbitrary weights?

## Search and source selection

- Concepts: dynamic topic models, temporal document networks, multilevel IRT,
  multiple-membership multiple-classification, latent-space IRT, and
  multilevel case-deletion diagnostics.
- Priority: peer-reviewed primary papers, official proceedings, accepted
  author manuscripts, TEPP's approved PRD/ADR, and fast-mlsirm's normative
  ADR/research register.
- Excluded as authorities: review-only pages, vendor summaries, lexical topic
  matching, engagement ranking, and methods that do not preserve posterior,
  time, relation, or membership identity.

## Findings

### Temporal topic identity and document relations

Blei and Lafferty (2006) establish state-space topic evolution rather than
independent time-bin models. Zhang and Lauw (2022) jointly model temporal
document topics and network structure; this directly supports consuming
explicit Event Lineage as relational evidence rather than matching topic
labels after fitting. TEPP PRD v0.4 and ADR 0012 combine those concerns in the
TRSL-TM producer boundary, including global topic identity, posterior
coordinates, multiple clocks, relations, and cross-classified membership.

The evidence does not establish that every relation is causal or that a
reactivated topic is newly born. Those states and lineage events must arrive
from a versioned TEPP result.

### Multilevel and multiple-membership measurement

Fox and Glas (2001) show why latent rather than observed scores should be
modeled jointly with cluster effects and measurement error. Browne, Goldstein,
and Rasbash (2001) define crossed and weighted multiple-membership structures.
Jin et al. (2022) demonstrate a multilevel network item-response model that
can expose differences missed by conventional multilevel models. These papers
support distinct business-unit, PU, team, and person dimensions with explicit
time-valid membership; they do not support inferring equal weights when the
source has none.

### “Important post” estimand

Shi and Chen (2008) define case-deletion diagnostics at multiple levels for
fixed and random parameters. ADR 0210 therefore gives importance the bounded
name **model influence** and defines it as observed-information-scaled change
in the topic-by-context estimate after deleting the complete post
observation. This answers sensitivity of the fitted model, not business value
or causality. Molenaar and Jeon (2026) support recovery-tested regularized JML
for latent-space IRT, but do not by themselves validate this product-specific
construct; the fast-mlsirm producer must implement and recover the exact
versioned influence estimand before LineageWeave activates it.

## Architecture consequence

LineageWeave is a strict consumer. TEPP owns temporal/relational topic
posterior arithmetic. fast-mlsirm owns multilevel multiple-membership fitting,
observed information, deletion refits, posterior-draw combination, and CPU/GPU
parity in Rust. LineageWeave persists exact accepted artifacts, applies ABAC,
and renders tied exact values; it adds no threshold, fallback score, or local
numerical formula.

## Primary sources (APA 7th)

See [ADR 0210](adr/0210-temporal-topic-context-influence-dashboard.md#references-apa-7th)
for the full APA 7 bibliography and exact architecture mapping.

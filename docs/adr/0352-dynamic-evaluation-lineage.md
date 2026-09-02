# ADR 0352: Project dynamic evaluation snapshots without absorbing decision authority

- Status: Proposed
- Date: 2026-09-02
- Depends on: ADR 0300 (contextual-orchestrator ownership boundary), ADR 0301 (dichotomous measurement policy)

## Context

A product evaluation may resolve its concrete items dynamically from an authored
blueprint, a production sample, a controlled perturbation, or a model/algorithmic
generator. A fixed item set or validated anchor corpus may not exist during cold
start. Nevertheless, an evaluation must remain reproducible enough to determine
which exact item snapshots, generator invocations, rater observations,
adjudication artifacts, calibration evidence, and promotion decisions informed a
result.

A single mutable `evaluation_item` record would collapse independent facts and
permit later review to rewrite history. It could also allow LineageWeave to absorb
provider credentials, model routing, psychometric calculation, hosted
adjudication, or source-system authority that belongs to other bounded contexts.

Opaque provenance references also cross service and rendering boundaries. Unicode
format controls can be machine-distinct while remaining visually absent or
changing bidirectional presentation, creating an avoidable alias/spoofing surface
for identifiers used in equality and provenance joins. Unicode Technical Standard
#39 treats identifier ambiguity and default-ignorable characters as security
concerns. LineageWeave therefore rejects Unicode `Cf` format controls in these
opaque references rather than normalizing them into a guessed identity. This is a
product-specific restrictive profile, not a claim of full UTS #39 conformance.

## Decision

LineageWeave publishes the source-text-free
`lineageweave_dynamic_evaluation_lineage/v1` projection. It contains two sealed
aggregate forms.

### Dynamic evaluation item lineage

One item projection records only immutable references:

- exact item-snapshot and blueprint-revision identity;
- exact released source-contract identity and complete lowercase SHA-256 digest;
- optional item-generation invocation;
- zero or more immutable rater-invocation references;
- optional adjudication-case and separate adjudication-resolution references;
- zero or more calibration-artifact references;
- optional separate anchor-promotion decision;
- optional predecessor item snapshot that this version supersedes.

An adjudication resolution requires its case. The source rater invocations remain
present and are never replaced by the resolution. A successor may identify an
older snapshot but cannot supersede itself.

### Dynamic evaluation run lineage

One run projection freezes:

- one exact run-snapshot and blueprint-revision identity;
- one non-empty, unique, blueprint-consistent item set;
- zero or more item snapshots explicitly acting as anchors;
- one comparability state: `unavailable`, `within_run_only`, or `linked`;
- an immutable linking-evidence reference only when comparability is `linked`.

Cold-start runs with zero fixed anchors are valid for pilot, diagnostic, and
within-run evidence collection. They cannot claim cross-version linked scores.

An item can appear in `anchor_item_snapshot_refs` only when its lineage includes
both separate calibration evidence and an anchor-promotion decision. An
adjudication resolution alone is insufficient. `linked` additionally requires at
least one such promoted anchor and independent linking evidence.

## Ownership boundary

LineageWeave owns product-specific source/rubric/instrument provenance and the
projection that lets a buyer reconstruct how evidence artifacts relate. It does
not create the foreign artifacts it references.

- contextual-orchestrator owns provider/model execution, routing, fallback,
  dynamic item-generation invocation evidence, and rater-observation creation.
- fast-mlsirm owns reusable measurement Published Languages and all production
  psychometric calibration, fit, DIF, information, linking, uncertainty, and
  score arithmetic.
- Psychometrics Commons owns hosted blueprint/run lifecycle, panel assignment,
  adjudication transaction state, tenant authorization, persistence, and
  immutable result publication.
- TEPP owns temporal/event semantics and later drift, change-point, or invariance
  monitoring.

Cross-repository integration must consume immutable released/versioned artifacts
with exact digests. Mutable sibling PR heads, foreign service databases, and
cross-service SQL are not production contracts.

## Fail-closed behavior

The projection rejects:

- provider credentials, endpoints, provider/model selection fields, scores,
  latent traits, pass/fail, certification, employment decisions, or embedded
  adjudication decisions;
- unknown fields and non-string mapping keys;
- empty, padded, Unicode-format-control-bearing, control-bearing,
  surrogate-bearing, or overlong opaque references;
- malformed or non-lowercase contract digests;
- duplicate item/rater/calibration/anchor references;
- item sets beyond the bounded allocation ceiling;
- mixed blueprint revisions in one run snapshot;
- a resolution without a case or self-supersession;
- anchor claims without separate calibration and promotion evidence;
- linked comparability without promoted anchors and linking evidence;
- linking evidence on an unavailable or within-run-only projection.

No missing reference is converted into a score, default anchor, provider guess,
or synthetic lineage edge.

## Consequences

### Benefits

- dynamic evaluations can begin before a fixed item corpus exists;
- each run remains tied to its actual immutable item set rather than a mutable
  blueprint or regenerated approximation;
- adjudication remains review evidence instead of overwriting observations;
- anchor promotion, calibration, and linking remain separately auditable;
- opaque references cannot differ only through invisible Unicode format controls;
- LineageWeave can display an explicit no-anchor/no-linking limitation without
  inventing comparability;
- provider and psychometric authorities remain in their canonical owners.

### Costs

- the hosted system must persist the referenced run and item snapshots before
  dispatching observations;
- downstream projections require released contract versions and digests;
- source content remains separately permissioned and cannot be recovered from
  this metadata-only envelope;
- external adapters must map any legitimate foreign identifier containing a
  rejected format control to a separate canonical released reference instead of
  passing it through unchanged;
- user interfaces must distinguish provisional, adjudicated, calibrated,
  promoted-anchor, and linked states rather than displaying one generic
  “evaluated” badge.

## Alternatives considered

1. **Reuse a mutable golden-prompt table.** Rejected because no fixed set is
   required, “golden” conflates adjudication with validation, and later edits
   would destroy run identity.
2. **Store provider/model payloads in LineageWeave.** Rejected because provider
   execution and credential policy belong to contextual-orchestrator and raw
   content has separate access/retention requirements.
3. **Treat adjudicated items as anchors automatically.** Rejected because an
   adjudication resolution does not establish calibration, fit, fairness,
   invariance, approval, or cross-version linking.
4. **Block all evaluation until anchors exist.** Rejected because governed pilot
   and diagnostic evidence is necessary to create and validate the first anchor
   corpus.
5. **Silently strip or normalize format controls.** Rejected because mutation
   could collapse two foreign references into an identity that the owning system
   never published. Admission fails closed instead.

## Verification

Focused tests cover zero-anchor runs, adjudication/source-observation separation,
anchor-promotion requirements, linked-evidence requirements, immutable collection
copying, strict mapping admission, reference and digest hygiene, blueprint
consistency, duplicate and resource limits, public exports, and direct-construction
seals. Reference hygiene includes zero-width and bidirectional Unicode format
controls. The new projection module must retain complete statement and branch
coverage on the unchanged exact head.

No fixed production item example, provider call, score, database migration, or
adjudication action is introduced by this ADR.

## References

American Educational Research Association, American Psychological Association,
& National Council on Measurement in Education. (2014). *Standards for
educational and psychological testing*. American Educational Research
Association.

Evans, E. (2003). *Domain-driven design: Tackling complexity in the heart of
software*. Addison-Wesley.

Moreau, L., Missier, P., Belhajjame, K., B’Far, R., Cheney, J., Coppens, S.,
Cresswell, S., Gil, Y., Groth, P., Klyne, G., Lebo, T., McCusker, J., Miles, S.,
Myers, J., Sahoo, S., & Tilmes, C. (2013). PROV-DM: The PROV data model. World
Wide Web Consortium.

Unicode Consortium. (2025). *Unicode security mechanisms* (Unicode Technical
Standard #39, Version 17.0.0, Revision 32). https://www.unicode.org/reports/tr39/

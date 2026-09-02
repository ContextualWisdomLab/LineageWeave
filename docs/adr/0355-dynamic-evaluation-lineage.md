# ADR 0355: Project dynamic evaluation snapshots without absorbing decision authority

- Status: Proposed
- Date: 2026-09-02
- Depends on: ADR 0300 (contextual-orchestrator ownership boundary), ADR 0301 (dichotomous measurement policy)

## Context

A product evaluation may resolve its concrete items dynamically from an authored
blueprint, a production sample, a controlled perturbation, or a model/algorithmic
generator. A fixed item set or validated anchor corpus may not exist during cold
start. Nevertheless, an evaluation must remain reproducible enough to determine
which exact substantive criteria, item snapshots, generator invocations, rater
observations, adjudication artifacts, calibration evidence, and promotion
decisions informed a result.

Item provenance without criterion provenance is insufficient: two runs can use the
same nominal rubric label while differing in intended use, construct, population,
language, domain, evidence-admission rules, missingness semantics, or response
category definitions. A run therefore cannot claim an auditable evaluation merely
because its generated items and observations are traceable.

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

The run contract admits as many as 10,000 item snapshots. A supersession-cycle
check that restarts a full predecessor walk from every item can therefore turn an
otherwise linear lineage admission into quadratic work. Admission cost is part of
the bounded-context integrity boundary: hostile or merely large valid input must
not obtain disproportionate CPU work before the projection can fail closed.

## Decision

LineageWeave publishes the source-text-free
`lineageweave_dynamic_evaluation_lineage/v1` projection. Substantive criterion
lineage is frozen independently and then bound into item/run lineage rather than
being inferred from an item generator or later score.

### Evaluation criterion-set lineage

One administered criterion-set snapshot retains:

- exact criterion-set identity and complete lowercase SHA-256 digest;
- the exact blueprint and rubric revision;
- intended-use, construct, population-scope, language-scope, and domain-scope
  references;
- a non-empty bounded set of uniquely identified criteria.

Each criterion retains exact definition, admissible-evidence, exclusion,
response-semantics, abstention, and not-observable rule references plus their
complete digests, together with the ordered response-category definition
references and digests. LineageWeave retains these product semantics but does not
turn them into fitted psychometric parameters or scoring authority.

### Dynamic evaluation item lineage

One item projection records only immutable references:

- exact item-snapshot and blueprint-revision identity;
- exact released source-contract identity and complete lowercase SHA-256 digest;
- when criterion-bound, the exact criterion-set snapshot/digest, rubric revision,
  and one or more governed criterion references;
- optional item-generation invocation;
- zero or more immutable rater-invocation references;
- optional adjudication-case and separate adjudication-resolution references;
- zero or more calibration-artifact references;
- optional separate anchor-promotion decision;
- optional predecessor item snapshot that this version supersedes.

An adjudication resolution requires its case. The source rater invocations remain
present and are never replaced by the resolution. A successor may identify an
older snapshot but cannot supersede itself.

Criterion binding is all-or-nothing at the item boundary: a partial set identity,
digest, rubric, or criterion list is rejected rather than treated as an unbound
item.

### Dynamic evaluation run lineage

One run projection freezes:

- one exact run-snapshot and blueprint-revision identity;
- one non-empty, unique, blueprint-consistent item set;
- when substantive criteria are administered, the complete immutable criterion
  set used for that run;
- zero or more item snapshots explicitly acting as anchors;
- one comparability state: `unavailable`, `within_run_only`, or `linked`;
- an immutable linking-evidence reference only when comparability is `linked`.

When a criterion set is supplied, every item must retain the same criterion-set
snapshot/digest and rubric revision, may reference only criteria in that set, and
the union of item criterion references must cover every administered criterion.
Criterion-bound items without their administered criterion set fail closed.

Cold-start runs with zero fixed anchors are valid for pilot, diagnostic, and
within-run evidence collection. They cannot claim cross-version linked scores.

An item can appear in `anchor_item_snapshot_refs` only when its lineage includes
both calibration evidence and an anchor-promotion decision. Within this v1
projection those evidence roles must also retain distinct opaque identities: the
promotion decision cannot reuse a calibration-artifact reference. An adjudication
resolution alone is insufficient. `linked` additionally requires at least one such
promoted anchor and independent linking evidence; the linking-evidence identity
cannot reuse that promoted anchor's promotion or calibration reference. This
identity-separation rule is a LineageWeave auditability invariant, not a claim
that a psychometric standard universally requires physically separate files or
storage objects.

In-run `supersedes_item_snapshot_ref` edges form a finite functional graph. A
directed cycle fails closed. Validation records completed predecessor paths so an
in-run item is not repeatedly re-walked from every later successor; admission work
therefore remains linear in the admitted in-run items and edges. A predecessor
reference outside the supplied run terminates the local traversal rather than
inventing foreign graph truth.

## Ownership boundary

LineageWeave owns product-specific criterion/rubric/source/instrument provenance
and the projection that lets a buyer reconstruct how evidence artifacts relate.
It does not create the foreign artifacts it references.

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
cross-service SQL are not production contracts. Synthetic tests use synthetic
source-contract identities; they must not imply that an owner repository has
published a media type or schema that does not exist in an immutable release.

## Fail-closed behavior

The projection rejects:

- provider credentials, endpoints, provider/model selection fields, scores,
  latent traits, pass/fail, certification, employment decisions, or embedded
  adjudication decisions;
- unknown fields and non-string mapping keys;
- empty, padded, Unicode-format-control-bearing, control-bearing,
  surrogate-bearing, or overlong opaque references;
- malformed or non-lowercase contract digests;
- empty criterion sets, duplicate criterion identities, malformed category
  definition/digest cardinality, and incomplete substantive criterion meaning;
- partial item criterion bindings;
- criterion-bound items without their administered criterion set;
- criterion-set/blueprint, criterion-set/digest, rubric, or item-criterion
  substitution and incomplete administered-criterion coverage;
- duplicate item/rater/calibration/anchor references;
- item sets beyond the bounded allocation ceiling;
- mixed blueprint revisions in one run snapshot;
- a resolution without a case or self-supersession;
- directed cycles among supersession edges whose endpoints are in the run;
- anchor claims without calibration and promotion evidence, or with one opaque
  identity reused for both roles;
- linked comparability without promoted anchors and linking evidence, or with
  linking evidence whose identity reuses the promoted anchor's calibration or
  promotion evidence;
- linking evidence on an unavailable or within-run-only projection.

No missing criterion, reference, or evidence artifact is converted into a score,
default anchor, provider guess, or synthetic lineage edge.

## Consequences

### Benefits

- dynamic evaluations can begin before a fixed item corpus exists;
- the intended construct and evidence rules remain inspectable independently of
  item generation and later observations;
- each run remains tied to its actual immutable criterion/item set rather than a
  mutable rubric label, blueprint, or regenerated approximation;
- adjudication remains review evidence instead of overwriting observations;
- anchor promotion, calibration, and linking remain separately auditable;
- synthetic fixtures cannot masquerade as a released owner contract merely by
  using an owner-like identifier;
- opaque references cannot differ only through invisible Unicode format controls;
- large acyclic supersession chains stay bounded to linear graph-validation work;
- LineageWeave can display explicit criterion, no-anchor, and no-linking
  limitations without inventing comparability;
- provider and psychometric authorities remain in their canonical owners.

### Costs

- the hosted system must persist the referenced criterion, run, and item snapshots
  before observations are interpreted;
- downstream projections require released contract versions and digests;
- source content remains separately permissioned and cannot be recovered from
  this metadata-only envelope;
- external adapters must map any legitimate foreign identifier containing a
  rejected format control to a separate canonical released reference instead of
  passing it through unchanged;
- user interfaces must distinguish criterion meaning, provisional observation,
  adjudicated, calibrated, promoted-anchor, and linked states rather than
  displaying one generic “evaluated” badge.

## Alternatives considered

1. **Reuse a mutable golden-prompt table.** Rejected because no fixed set is
   required, “golden” conflates adjudication with validation, and later edits
   would destroy run identity.
2. **Persist only criterion identifiers or a rubric name.** Rejected because an
   identifier alone does not freeze intended use, construct/scope, evidence and
   exclusion rules, response/missingness semantics, or category definitions.
3. **Store provider/model payloads in LineageWeave.** Rejected because provider
   execution and credential policy belong to contextual-orchestrator and raw
   content has separate access/retention requirements.
4. **Treat adjudicated items as anchors automatically.** Rejected because an
   adjudication resolution does not establish calibration, fit, fairness,
   invariance, approval, or cross-version linking.
5. **Block all evaluation until anchors exist.** Rejected because governed pilot
   and diagnostic evidence is necessary to create and validate the first anchor
   corpus.
6. **Silently strip or normalize format controls.** Rejected because mutation
   could collapse two foreign references into an identity that the owning system
   never published. Admission fails closed instead.
7. **Re-walk the complete supersession prefix from every item.** Rejected because
   the 10,000-item admission budget would permit quadratic validation work even
   for a valid acyclic chain. Completed-path memoization preserves the same local
   graph semantics without that amplification.
8. **Name a synthetic test fixture after an unreleased owner contract.** Rejected
   because it makes a test value look like versioned cross-repository evidence.
   Synthetic fixtures use an explicitly synthetic identity; production adapters
   must provide the real released owner identity and digest.

## Verification

Focused tests cover substantive criterion completeness, criterion-set/item
binding, administered-criterion coverage, set/digest/rubric substitution,
zero-anchor runs, adjudication/source-observation separation, anchor-promotion
requirements, anchor/promotion/linking identity separation, linked-evidence
requirements, immutable collection copying, strict mapping admission, reference
and digest hygiene, blueprint consistency, duplicate and resource limits, public
exports, direct-construction seals, in-run supersession cycles, and long acyclic
supersession chains. Reference hygiene includes zero-width and bidirectional
Unicode format controls.

The supersession admission regression counts set membership/add work rather than
asserting a runner-specific elapsed-time threshold. That makes the complexity
contract deterministic while leaving real buyer-path latency to the repository's
separate measured performance evidence. The new projection modules must retain
complete statement and branch coverage on the unchanged exact head.

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

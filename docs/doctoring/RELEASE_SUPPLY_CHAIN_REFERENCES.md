# Release supply-chain references

**Supporting evidence for:** ADR 0361
**Reviewed:** 2026-09-04
**Status:** Non-normative doctoring evidence. ADR 0361 remains the decision authority.

This note records the authoritative external standards, platform contracts and
canonical-owner implementation evidence used while defining LineageWeave's
immutable release boundary. It does not promote an unimplemented workflow or a
queued check to release evidence.

## Current authoritative baseline

### CycloneDX 1.7

The CycloneDX specification overview identifies **1.7** as the current
specification version and gives its release date as 2025-10-21. ADR 0361 uses
CycloneDX 1.7 only for the per-distribution SBOM representation; LineageWeave
does not claim that a generic repository-directory SBOM is an attestation of
one exact wheel or source distribution.

CycloneDX Core Working Group. (2025). *CycloneDX specification 1.7*. OWASP
Foundation. https://cyclonedx.org/specification/overview/

### SLSA 1.2

The SLSA project announced Version **1.2** as the approved release on
2025-11-24. ADR 0361 uses SLSA as supply-chain threat/provenance grounding; it
does not claim a SLSA level merely because a workflow uses provenance or a
reusable workflow.

Open Source Security Foundation. (2025, November 24). *Announcing SLSA v1.2*.
https://slsa.dev/blog/2025/11/announce-slsa-v1.2

### GitHub artifact attestations

GitHub's current documentation requires explicit attestation/OIDC permissions
for credentialed provenance generation and documents verification of artifact
attestations. ADR 0361 therefore keeps pull-request-controlled build work in an
unprivileged job and delegates credentialed attestation to the canonical
organization reusable only after inert exact-artifact verification.

GitHub. (n.d.). *Using artifact attestations to establish provenance for
builds*. GitHub Docs. Retrieved September 3, 2026, from
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

GitHub. (n.d.). *Using artifact attestations*. GitHub Docs. Retrieved September
3, 2026, from
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations

### Canonical exact-artifact handoff

The circular transport-receipt defect originally tracked by
`ContextualWisdomLab/.github#1782` is resolved by merged `.github#1791`. The
reviewed immutable owner commit for LineageWeave is
`bd866a21cca2a7e709f0b7a88150c310a9d98239`, and the consumer surface is:

`ContextualWisdomLab/.github/.github/workflows/exact-artifact-sbom-attestation.yml@bd866a21cca2a7e709f0b7a88150c310a9d98239`

At that commit, `source-identity.json` contains the inner source/artifact
identity only: schema version, source repository/SHA, evidence artifact name,
predicate/schema and exact wheel/sdist plus SBOM filenames and SHA-256 values.
It does not contain the post-upload GitHub artifact digest. The reusable keeps
`evidence_artifact_id`, `evidence_artifact_name` and
`evidence_artifact_digest` as outer receipt inputs, independently queries the
same-run GitHub Actions artifact metadata, requires exact ID/name/digest/run and
non-expired state before download, and repeats that receipt verification inside
the credentialed signer boundary. The six-file cardinality, strict JSON,
checksums and exact-subject CycloneDX validation remain fail closed.

The current protected `.github/main` descends from the repair commit, but ADR
0361 pins the reviewed repair commit itself rather than a moving default branch.
A later owner revision is a new dependency change requiring normal review and
fresh exact evidence.

ContextualWisdomLab. (2026). *fix(release): make exact artifact handoff acyclic*
(PR #1791). GitHub.

### GitHub immutable releases

GitHub documents immutable releases as a repository/organization control that
locks a published release's associated tag and assets. Publication also creates
a release attestation. GitHub recommends creating a draft release, attaching
all assets, and publishing the populated draft so immutability does not leave a
partially populated release.

The repository REST API exposes `GET /repos/{owner}/{repo}/immutable-releases`
and returns an object containing `enabled` and `enforced_by_owner`. For ADR 0361
both must be true: `enabled: true` proves the feature is active and
`enforced_by_owner: true` proves repository administrators cannot locally turn
it off during the release interval. The administrative read capability used to
inspect that state belongs only to the trusted release boundary.

The Release REST representation exposes the exact Release ID, `tag_name`,
`draft`, `prerelease`, asset list and asset digests, and published releases
report whether they are `immutable`. ADR 0361 therefore treats a final settings
read alone as insufficient. Immediately before publish it re-reads the exact
Release ID, requires `draft: true`, the admitted `tag_name`,
`prerelease: false`, and the exact sealed asset name/digest set, then repeats the
annotated-tag object/commit check. After publication it requires
`immutable: true` and verifies the same tag/assets again.

GitHub documents no consumer-supplied compare-and-publish precondition that
atomically binds those prior REST reads to publication. The architecture does
not invent one. The controllable race is narrowed with three mandatory
configuration/serialization controls: owner-enforced release immutability, a
reviewed ruleset protecting the candidate release-tag namespace, and one
exclusively serialized **trusted release writer** for candidate tag/ref and
Release mutations. If those controls are absent or cannot be proved, release
publication stays RED.

That same ownership rule applies to abort cleanup. Verifying a candidate ref
and deleting it in separate unsynchronized calls leaves a TOCTOU window. ADR
0361 therefore defines candidate ref removal as **compare-and-delete** under the
same trusted release writer and protected tag namespace: compare the live ref
with the recorded tag-object SHA immediately before deletion and allow deletion
only when writer/ruleset serialization prevents another admitted writer from
retargeting it before the delete. If the platform configuration cannot provide
that guarantee, the ref is not deleted; the version is quarantined. Exact draft
identity, unpublished state, asset set and post-delete absent-state checks are
still required.

GitHub also states that once a tag has been associated with a published
immutable release, the tag name cannot be reused even after that release is
deleted. Possible publication therefore changes recovery to a new version
rather than cleanup/reuse.

GitHub. (n.d.). *Immutable releases*. GitHub Docs. Retrieved September 4, 2026,
from
https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases

GitHub. (n.d.). *Preventing changes to your releases*. GitHub Docs. Retrieved
September 4, 2026, from
https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes

GitHub. (n.d.). *REST API endpoints for repositories*. GitHub Docs. Retrieved
September 4, 2026, from https://docs.github.com/en/rest/repos/repos

GitHub. (n.d.). *REST API endpoints for releases*. GitHub Docs. Retrieved
September 4, 2026, from https://docs.github.com/en/rest/releases/releases

### GitHub annotated tag identity

GitHub's Git data APIs distinguish the tag reference from an annotated tag
object. Creating an annotated tag requires creating a Git tag object and then a
`refs/tags/<tag>` reference that points to that object. The tag object separately
records its target object type and target SHA; GitHub documents `commit`,
`tree`, and `blob` as possible target types for tag-object creation. Therefore a
trusted release verifier cannot compare the tag ref's object SHA directly with
the protected source commit SHA. For ADR 0361 the release tag is valid only when
the ref resolves to the expected annotated tag object, that object has target
type `commit`, and the peeled target SHA equals the exact protected source SHA.
Missing refs/tag objects, non-commit targets, and mismatched target SHAs fail
closed before publication and again during post-publication verification.

GitHub. (n.d.). *REST API endpoints for Git references*. GitHub Docs. Retrieved
September 4, 2026, from https://docs.github.com/en/rest/git/refs

GitHub. (n.d.). *REST API endpoints for Git tags*. GitHub Docs. Retrieved
September 4, 2026, from https://docs.github.com/en/rest/git/tags

### JSON strictness

The canonical `.github` verifier rejects duplicate JSON properties, non-finite
numbers, invalid UTF-8 and unexpected evidence members before trusting the
handoff. RFC 8259 is the interoperability baseline for the JSON representation;
repository-specific stricter validation remains a security profile rather than
a claim that RFC 8259 itself mandates every fail-closed rule used by the
verifier.

Bray, T. (2017). *The JavaScript Object Notation (JSON) data interchange
format* (RFC 8259). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8259

## Traceability to ADR 0361

- exact wheel/sdist SBOM representation → CycloneDX 1.7;
- source/build provenance threat model → SLSA 1.2;
- credential separation and artifact-attestation verification → GitHub artifact
  attestation documentation;
- acyclic inner identity plus immutable outer GitHub Actions artifact receipt →
  `ContextualWisdomLab/.github#1791` at
  `bd866a21cca2a7e709f0b7a88150c310a9d98239`;
- owner-enforced immutable-release admission, exact draft/asset verification,
  protected tag namespace, trusted-writer serialization and post-publication
  `immutable: true` verification → GitHub immutable release, repository and
  Release REST documentation;
- conditional candidate-ref compare-and-delete and quarantine on missing
  serialization → the CWE-367 recovery boundary derived from those GitHub API
  semantics; no undocumented atomic REST primitive is assumed;
- annotated-tag ref/object separation and exact source-commit peeling → GitHub
  Git references and Git tags REST documentation;
- strict machine-readable evidence intake → RFC 8259 plus the stricter
  canonical `.github` verifier contract.

External standards do not override the current canonical owner implementation.
LineageWeave consumes only the reviewed immutable owner SHA above; moving to a
later `.github` revision requires a normal dependency review and regenerated
exact-head evidence.

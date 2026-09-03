# ADR 0358 — Immutable release supply-chain boundary

**Decision status:** Proposed
**Date:** 2026-09-03
**Related:** ContextualWisdomLab/.github#1782, LineageWeave #911

## Context

LineageWeave does not currently publish an immutable GitHub release from a
product-local release workflow. The protected product line is versioned as a
Python package, but release evidence must identify one exact protected source
commit, the exact wheel and source distribution built from that commit, their
software bills of materials, and the immutable publication that buyers can
verify later.

The organization already owns the reusable trust boundary for exact-artifact
SBOM attestation in `ContextualWisdomLab/.github`. LineageWeave must consume
that boundary rather than copy signing, OIDC, attestation-verification, or
provider policy into this repository.

A fresh integration attempt exposed a canonical-owner prerequisite at
`ContextualWisdomLab/.github#1782`. The current reusable workflow requires the
GitHub Actions artifact digest as an input and also requires
`source-identity.json` *inside the same artifact* to contain that digest. The
artifact digest cannot be known until the artifact has been uploaded, while
changing the identity file changes the bytes whose digest GitHub computes.
That circular dependency makes the current handoff impossible to construct by
a deterministic caller without weakening the verifier. This ADR therefore
keeps the release integration Proposed until the canonical owner publishes an
acyclic exact-SHA contract.

LineageWeave also cannot publish a commercial release from protected `main`
while the reachable synchronous PostgreSQL tooling path still contains the
LGPL-family `psycopg2-binary` dependency. PR #911 owns its replacement and the
reproducible lockfile migration. Release work must consume that merged,
license-clean protected result; it must not waive or suppress the inventory.

GitHub's immutable-release setting is a separate repository/organization
control from artifact attestation. GitHub documents that a published immutable
release locks the associated tag and assets, and automatically creates a
release attestation. It also exposes an authenticated repository endpoint,
`GET /repos/{owner}/{repo}/immutable-releases`, that returns success only when
release immutability is enabled. The release caller therefore needs an
administrative read-only preflight credential isolated from pull-request and
build execution; absence of that credential or an unsuccessful preflight is a
release-admission failure, not a reason to publish a mutable release.

GitHub's Git data model also distinguishes an annotated tag reference from the
commit that the tag names. `refs/tags/<version>` points to a Git tag object;
that tag object in turn names its target object and target type. A release
contract that compares the ref's tag-object SHA directly with the protected
source commit SHA would therefore reject a valid annotated tag or, worse,
encode the wrong identity rule. The release boundary must peel the annotated
tag object and admit only a target with type `commit` and the exact protected
source SHA.

## Decision

1. LineageWeave owns the product-local release caller: release readiness,
   package build, exact artifact preparation, release notes, tag creation,
   immutable GitHub Release publication, reproducibility checks, and rollback
   instructions.
2. `ContextualWisdomLab/.github` owns the reusable credentialed SBOM
   attestation and verification boundary. The LineageWeave caller must invoke
   a reviewed exact commit SHA of that reusable workflow. It must not vendor or
   fork the trusted verifier to make a local release pass.
3. Release initiation is allowed only from the exact protected LineageWeave
   `main` commit being released. A version is valid only when package metadata,
   changelog/release notes, tag, distribution metadata, source identity and
   GitHub Release all name the same canonical `MAJOR.MINOR.PATCH` version and
   source SHA.
4. The unprivileged build stage receives `contents: read` only. It repeats the
   repository's complete release-relevant test, documentation, lockfile,
   security-contract and package checks before building a wheel and source
   distribution. Pull-request-controlled source never receives OIDC,
   attestation, release or package-publication credentials.
5. The build stage prepares one sealed evidence handoff containing exactly the
   wheel, source distribution, one CycloneDX 1.7 SBOM bound to each exact
   distribution, `source-identity.json`, and `checksums.sha256`. The inner
   source identity binds repository, exact source SHA, predicate/schema,
   distribution filenames and distribution/SBOM SHA-256 values. The canonical
   owner decides the final acyclic representation after `.github#1782`.
6. GitHub's uploaded artifact ID/name/digest is an outer immutable transport
   receipt. After `.github#1782` is repaired, the caller passes the returned
   receipt and exact inner identities to the canonical reusable workflow. The
   reusable workflow must independently revalidate the same-run receipt and
   inert handoff before any OIDC token or attestation permission becomes
   available.
7. Immutable publication occurs only after the exact artifact set has passed
   canonical attestation verification and repository release immutability has
   been independently admitted. Before tag creation or Release publication, a
   trusted preflight calls `GET /repos/{owner}/{repo}/immutable-releases` with
   the minimum GitHub Administration (read) permission. Only an authenticated
   success response that confirms `enabled: true` is admissible. A 404,
   permission failure, transport/API failure, malformed response, or any result
   that does not confirm `enabled: true` must fail closed before tag creation.
   The preflight credential is unavailable to pull-request and unprivileged
   build jobs.
8. After that preflight, the release job creates an annotated tag object whose
   target type is `commit` and whose target SHA is the exact protected source
   SHA admitted for the release, then creates `refs/tags/<version>` pointing to
   that tag object. Lightweight tags, tree/blob targets, existing refs, or a
   tag object targeting any other commit are inadmissible. The job then creates
   a draft GitHub Release and attaches the complete verified asset set.
   Immediately before publish, the trusted release boundary must recheck
   `GET /repos/{owner}/{repo}/immutable-releases` and re-resolve the tag. For
   the annotated tag, the ref's object SHA is the tag-object SHA, not the source
   commit SHA; the boundary must fetch that tag object and peel its target,
   require target type `commit`, and compare the peeled commit SHA with the
   exact protected source SHA. It must never compare the tag-object SHA itself
   with the source commit SHA. Any setting change, lookup/API failure,
   malformed response, missing ref/tag object, unexpected target type, or
   peeled commit/source SHA mismatch must fail closed while the draft remains
   unpublished. Only after this second admission may the draft be published as
   the immutable non-prerelease release. This closes the
   time-of-check/time-of-use interval between the initial immutability admission
   and publication. It must not overwrite an existing tag, asset or version. A
   failed or partial publication is an incident, not permission to mutate
   previously published bytes under the same identity.
9. Reproducibility is tested by rebuilding the wheel and source distribution
   from the same protected source under the reviewed toolchain and comparing
   the release contract's declared deterministic subjects. Any known
   nondeterministic field must be removed or normalized by source/tooling
   repair; it is not excluded from comparison merely to obtain GREEN.
10. Rollback restores a previously reviewed workflow revision and produces new
    artifacts from a new protected commit/version. It does not move an existing
    release tag or reuse an old attestation for different bytes.
11. Package-registry publication is not inferred from a GitHub Release. If a
    registry such as PyPI is adopted, its protected environment, trusted
    publishing identity, independent review policy and immutable-version
    behavior require a separate accepted decision before credentials or
    publishing steps are added.

## RED / GREEN acceptance

The current RED is structural and owner-bound: LineageWeave has no product
release workflow, protected `main` is not yet license-clean, and the canonical
exact-artifact reusable cannot accept a deterministic first-party caller
because of `.github#1782`.

GREEN requires all of the following on one unchanged protected source SHA:

- #911 or a verified successor has removed the reachable disallowed dependency
  and committed a reproducible lock that passes the frozen dependency gate;
- `.github#1782` is fixed on protected `.github/main` and LineageWeave pins the
  repaired reusable workflow by exact commit SHA;
- a product-local release workflow builds wheel/sdist plus the exact six-file
  evidence handoff without credentialed execution of pull-request source;
- the canonical reusable verifies and attests the exact returned artifact
  receipt and exact wheel/sdist subjects;
- a trusted preflight calls `GET /repos/{owner}/{repo}/immutable-releases`
  before tag creation and confirms `enabled: true`; missing administrative-read
  capability or any non-confirming result must fail closed;
- the release-specific ref points to an annotated tag object whose target type
  is `commit` and whose peeled target is the exact protected source SHA; direct
  comparison of the tag-object SHA with the source commit SHA is forbidden;
- a clean rebuild proves the declared reproducibility contract;
- the complete verified asset set is attached to a draft GitHub Release;
- immediately before publish, the trusted boundary must recheck repository
  immutability and repeat the annotated-tag peel to prove the release tag still
  reaches the same exact protected source SHA; any non-confirming result must
  fail closed with the draft unpublished;
- release notes, version, protected source SHA, tag, distributions, SBOMs,
  attestations and immutable GitHub Release are mutually consistent; and
- rollback/incident instructions are exercised against synthetic release
  fixtures without deleting or rewriting valid published evidence.

Until every condition is evidenced, this ADR remains Proposed and no
LineageWeave release-readiness claim may cite this design as delivered.

## Alternatives considered

### Copy the central attestation workflow into LineageWeave

Rejected. It would create a second signing-policy authority, duplicate security
fixes and let a product repository bypass a defect in the canonical owner.

### Drop the GitHub artifact digest from verification locally

Rejected. The outer receipt protects the exact same-run transport handoff.
The circularity is an owner-contract modeling defect; weakening digest binding
in a consumer is not a causal repair.

### Publish without proving GitHub release immutability is enabled

Rejected. A release whose tag or assets remain mutable does not meet this
ADR's buyer-visible integrity claim. Failure to read the setting is also not
proof that the setting is enabled, so the publication path fails closed rather
than assuming repository configuration.

### Compare an annotated tag ref SHA directly with the source commit SHA

Rejected. For an annotated tag, the ref names a Git tag object rather than the
source commit. The trusted boundary must peel the tag object, require target
type `commit`, and compare that target SHA with the admitted source SHA.

### Publish a GitHub Release first and attach evidence later

Rejected. Buyers would observe a release identity before its exact artifact,
SBOM and provenance evidence was complete. GitHub's immutable-release guidance
also recommends attaching assets to a draft and publishing only after the
asset set is complete.

### Wait for a package registry before creating any release boundary

Rejected. GitHub Release immutability, exact source/artifact identity, SBOM,
provenance and rollback are independently valuable buyer controls. Registry
publication can be added later behind its own protected decision.

## Risks and follow-up

- The central reusable contract can change while `.github#1782` is repaired.
  LineageWeave must inspect the protected implementation and pin its exact SHA;
  no branch-name or mutable `main` reference is acceptable in release code.
- The immutable-release status endpoint requires administrative read access.
  That capability must be provisioned to the trusted release admission step
  only; it must not expand permissions for tests, builds, pull requests or the
  canonical attestation reusable. If it cannot be provisioned, publication
  remains RED.
- The repository immutability setting and release tag are mutable until the
  immutable release is published. A single early preflight therefore has a
  time-of-check/time-of-use window; both are revalidated immediately before
  publish and any drift leaves the draft unpublished.
- An annotated tag ref exposes a tag-object SHA. Implementations that skip the
  tag-object lookup can either produce a false mismatch or validate the wrong
  identity. Current-head tests must exercise annotated-tag success plus missing,
  non-commit-target and wrong-commit failures before release code can be GREEN.
- Reproducible Python distributions may expose timestamps, archive ordering or
  backend metadata that require causal build-system repair. A mismatch remains
  RED until explained and removed at the source.
- Current organization Actions queue saturation can delay evidence, but queue
  latency is not a reason to bypass release gates or transfer predecessor-head
  results.

## References

Bray, T. (2017). *The JavaScript Object Notation (JSON) data interchange
format* (RFC 8259). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8259

CycloneDX Core Working Group. (2025). *CycloneDX specification 1.7*.
OWASP Foundation. https://cyclonedx.org/specification/overview/

GitHub. (2026). *Immutable releases*. GitHub Docs.
https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases

GitHub. (2026). *REST API endpoints for repositories: Check if immutable
releases are enabled for a repository*. GitHub Docs.
https://docs.github.com/en/rest/repos/repos

GitHub. (2026). *REST API endpoints for Git references*. GitHub Docs.
https://docs.github.com/en/rest/git/refs

GitHub. (2026). *REST API endpoints for Git tags*. GitHub Docs.
https://docs.github.com/en/rest/git/tags

GitHub. (2026). *Using artifact attestations to establish provenance for
builds*. GitHub Docs.
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Open Source Security Foundation. (2025). *SLSA specification version 1.2*.
https://slsa.dev/spec/v1.2/

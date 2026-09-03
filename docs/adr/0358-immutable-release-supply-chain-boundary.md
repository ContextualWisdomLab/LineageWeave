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
   canonical attestation verification. The release job creates the tag against
   the already-verified protected source SHA and creates a non-draft,
   non-prerelease GitHub Release without overwriting an existing tag, asset or
   version. A failed or partial publication is an incident, not permission to
   mutate previously published bytes under the same identity.
8. Reproducibility is tested by rebuilding the wheel and source distribution
   from the same protected source under the reviewed toolchain and comparing
   the release contract's declared deterministic subjects. Any known
   nondeterministic field must be removed or normalized by source/tooling
   repair; it is not excluded from comparison merely to obtain GREEN.
9. Rollback restores a previously reviewed workflow revision and produces new
   artifacts from a new protected commit/version. It does not move an existing
   release tag or reuse an old attestation for different bytes.
10. Package-registry publication is not inferred from a GitHub Release. If a
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
- a clean rebuild proves the declared reproducibility contract;
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

### Publish a GitHub Release first and attach evidence later

Rejected. Buyers would observe a release identity before its exact artifact,
SBOM and provenance evidence was complete. Partial evidence cannot be promoted
as immutable release readiness.

### Wait for a package registry before creating any release boundary

Rejected. GitHub Release immutability, exact source/artifact identity, SBOM,
provenance and rollback are independently valuable buyer controls. Registry
publication can be added later behind its own protected decision.

## Risks and follow-up

- The central reusable contract can change while `.github#1782` is repaired.
  LineageWeave must inspect the protected implementation and pin its exact SHA;
  no branch-name or mutable `main` reference is acceptable in release code.
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

GitHub. (2026). *Using artifact attestations to establish provenance for
builds*. GitHub Docs.
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Open Source Security Foundation. (2025). *SLSA specification version 1.2*.
https://slsa.dev/spec/v1.2/

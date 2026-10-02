# ADR 0361 — Immutable release supply-chain boundary

**Decision status:** Proposed
**Date:** 2026-09-03
**Related:** ContextualWisdomLab/.github#1782, ContextualWisdomLab/.github#1791, LineageWeave #911

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

A prior integration attempt exposed the circular handoff defect tracked by
`ContextualWisdomLab/.github#1782`: the reusable required the post-upload GitHub
Actions artifact digest inside `source-identity.json`, even though that file was
part of the same upload whose bytes determine the digest. The canonical owner
repaired that model in merged `.github#1791`. Protected-owner commit
`bd866a21cca2a7e709f0b7a88150c310a9d98239` is the immutable consumer pin for
this decision. At that commit the inner source identity binds repository,
source SHA, predicate/schema and exact distribution/SBOM filenames and digests,
but not the outer GitHub artifact digest. The reusable independently verifies
the returned artifact ID/name/digest before downloading the sealed evidence and
again inside the credentialed signer boundary. This resolves the owner-side
cryptographic cycle without weakening transport-receipt verification.

LineageWeave still cannot publish a commercial release from protected `main`
while the reachable synchronous PostgreSQL tooling path contains the LGPL-family
`psycopg2-binary` dependency. PR #911 owns its replacement and the reproducible
lockfile migration. Release work must consume that merged, license-clean
protected result; it must not waive or suppress the inventory.

GitHub's immutable-release setting is a separate repository/organization
control from artifact attestation. GitHub documents that a published immutable
release locks the associated tag and assets and automatically creates a release
attestation. The repository API returns both `enabled` and `enforced_by_owner`
for immutable-release admission. For this high-assurance commercial release
path, repository-local enablement is not enough: the final publication boundary
requires owner-enforced immutability so a repository administrator cannot turn
the control off between admission and publish. The trusted release writer uses
only the administrative read capability needed to prove that state.

The API does not expose a consumer-supplied compare-and-publish precondition
that atomically couples an earlier settings/tag read to Release publication.
The release design therefore cannot treat two REST reads as atomic. It closes
the controllable races with mandatory configuration locks: owner-enforced
release immutability, a reviewed protected ruleset for the candidate tag
namespace, and one exclusively serialized trusted release writer for all
candidate tag/ref and Release mutations. If those controls cannot be proved,
publication remains RED.

GitHub's Git data model distinguishes an annotated tag reference from the
commit that the tag names. `refs/tags/<version>` points to a Git tag object;
that tag object separately names its target object and target type. The final
publish decision must therefore re-read the exact tag object, peel it to a
`commit`, and compare that target with the exact protected source SHA while the
protected/serialized candidate namespace prevents an admitted writer from
retargeting the ref.

The immutable protections begin at publication, not at draft creation. GitHub
recommends creating a draft, attaching all assets, and only then publishing it.
That creates a pre-publication interval in which the candidate tag, draft and
assets are already real identities. The final admission must revalidate the
exact Release ID, `draft: true`, `tag_name`, `prerelease: false`, and the full
asset name/digest set. Abort cleanup must likewise bind deletion to the exact
candidate under the same writer/ruleset serialization; otherwise cleanup is
quarantined rather than risking deletion of a retargeted ref.

## Decision

1. LineageWeave owns the product-local release caller: release readiness,
   package build, exact artifact preparation, release notes, tag creation,
   immutable GitHub Release publication, reproducibility checks, and rollback
   instructions.
2. `ContextualWisdomLab/.github` owns the reusable credentialed SBOM
   attestation and verification boundary. The LineageWeave caller must invoke
   `ContextualWisdomLab/.github/.github/workflows/exact-artifact-sbom-attestation.yml@bd866a21cca2a7e709f0b7a88150c310a9d98239`.
   It must not vendor or fork the trusted verifier, and a later mutable
   `.github/main` SHA does not replace this reviewed pin.
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
   distribution filenames and distribution/SBOM SHA-256 values. It deliberately
   excludes the post-upload GitHub Actions artifact digest; that value exists
   only in the outer transport receipt returned after upload.
6. GitHub's uploaded artifact ID/name/digest is an outer immutable transport
   receipt. The caller passes that returned receipt and the exact inner
   identities to the pinned canonical reusable. The reusable independently
   revalidates same-run artifact ID/name/digest and the inert handoff before any
   OIDC token or attestation permission becomes available, and repeats the
   outer-receipt verification inside the credentialed signer boundary.
7. Before any release tag or draft is created, enter a single **trusted release
   writer** serialized for the candidate version/tag namespace. Call
   `GET /repos/{owner}/{repo}/immutable-releases` and require both
   `enabled: true` and `enforced_by_owner: true`. Require a reviewed tag
   ruleset/protection receipt that prevents actors outside the trusted release
   writer from retargeting or deleting the candidate release-tag namespace.
   Any missing administrative-read capability, non-confirming settings result,
   absent protection receipt, or inability to prove writer serialization must
   **fail closed** before tag creation. These privileged controls are not
   available to pull-request or unprivileged build jobs.
8. After that admission, create an annotated tag object whose target type is
   `commit` and whose target SHA is the exact protected source SHA, then create
   `refs/tags/<version>` pointing to that object. Record the pre-create absence
   proof, exact tag-object SHA/ref and active protection receipt. Create a draft
   Release, retain its **exact Release ID**, require the creation receipt to be
   `draft: true` and `prerelease: false` with the exact admitted `tag_name`, and
   attach the complete verified asset set while recording every expected asset
   name and digest. **Immediately before publish**, while the same trusted
   release writer still owns the serialized namespace, recheck
   `GET /repos/{owner}/{repo}/immutable-releases` and again require
   `enabled: true` and `enforced_by_owner: true`; re-read the exact Release ID
   and require `draft: true`, exact `tag_name`, `prerelease: false`, and exact
   asset names/digests; then re-resolve the annotated tag, require the ref still
   names the recorded **tag object**, fetch it, **peel** its target, require
   **type `commit`**, and compare the peeled target with the **exact protected
   source SHA**. The owner-enforced setting, protected tag namespace and
   exclusively serialized trusted release writer are mandatory configuration
   locks for the interval that GitHub does not expose as one atomic API call.
   Any state drift, missing lock, mismatch, lookup failure or malformed response
   must **fail closed** with the draft unpublished. Only after all of those
   exact predicates remain true may the trusted writer publish the draft.
9. A failure after candidate tag/draft creation but before publication is a
   **pre-publication abort**. Same-version retry is admissible only after the
   trusted release writer proves from recorded receipts that the exact Release
   ID is still `draft: true`, unpublished, `prerelease: false`, names the exact
   candidate `tag_name`, and retains the exact candidate asset/digest set; the
   candidate ref still points to the recorded tag object; that tag object still
   peels to the admitted protected source commit; and no published release
   resolves for the tag. Delete only the exact draft ID after those proofs and
   re-resolve it as absent. Candidate tag deletion is a **compare-and-delete**
   under the same trusted release writer and protected namespace: immediately
   before deletion compare the live ref with the recorded tag-object SHA, and
   proceed only while serialization/protection guarantees that another admitted
   writer cannot change it before deletion. If compare-and-delete semantics or
   exclusive serialization cannot be guaranteed, do not delete or retarget the
   ref; quarantine the version. After an allowed deletion, re-resolve both draft
   and ref as absent before same-version retry. Never reuse a tag name that has
   been associated with a published immutable release.
10. Reproducibility is tested by rebuilding the wheel and source distribution
   from the same protected source under the reviewed toolchain and comparing
   the release contract's declared deterministic subjects. Any known
   nondeterministic field must be removed or normalized by source/tooling
   repair; it is not excluded from comparison merely to obtain GREEN.
11. Rollback restores a previously reviewed workflow revision and produces new
   artifacts from a new protected commit/version. It does not move an existing
   release tag or reuse an old attestation for different bytes. Once publication
   may have happened, remediation is forward-only; a tag name associated with a
   published immutable release is never reused even if that release is later
   deleted.
12. Package-registry publication is not inferred from a GitHub Release. If a
   registry such as PyPI is adopted, its protected environment, trusted
   publishing identity, independent review policy and immutable-version
   behavior require a separate accepted decision before credentials or
   publishing steps are added.

## RED / GREEN acceptance

The current RED is product-local: LineageWeave has no release workflow and
protected `main` is not yet license-clean. The former canonical handoff blocker
`.github#1782` is resolved by `.github#1791` and the reviewed owner pin
`bd866a21cca2a7e709f0b7a88150c310a9d98239`.

GREEN requires all of the following on one unchanged protected source SHA:

- #911 or a verified successor has removed the reachable disallowed dependency
  and committed a reproducible lock that passes the frozen dependency gate;
- the product-local workflow consumes
  `exact-artifact-sbom-attestation.yml@bd866a21cca2a7e709f0b7a88150c310a9d98239`
  rather than mutable `.github/main` or a copied verifier;
- a product-local release workflow builds wheel/sdist plus the exact six-file
  evidence handoff without credentialed execution of pull-request source;
- the canonical reusable verifies and attests the exact returned artifact
  receipt and exact wheel/sdist subjects;
- one trusted release writer has exclusive candidate-version serialization and
  an active protected tag namespace; the immutable-release preflight and final
  publish-boundary check both require `enabled: true` and
  `enforced_by_owner: true`;
- immediately before publish, the exact Release ID still has `draft: true`, the
  exact `tag_name`, `prerelease: false`, and the exact sealed asset name/digest
  set; the annotated tag ref still names the recorded tag object, which peels to
  type `commit` and the exact protected source SHA;
- a clean rebuild proves the declared reproducibility contract;
- post-publication verification observes the same release/tag/assets and
  `immutable: true`;
- synthetic release fixtures exercise pre-publication abort, conditional
  compare-and-delete, exact draft/tag ownership, quarantine when serialization
  cannot be proved, re-resolve-as-absent before same-version retry, and never
  reuse a tag associated with a published immutable release;
- release notes, version, protected source SHA, tag, distributions, SBOMs,
  attestations and immutable GitHub Release are mutually consistent; and
- rollback/incident instructions are exercised without deleting or rewriting
  valid published evidence.

Until every condition is evidenced, this ADR remains Proposed and no
LineageWeave release-readiness claim may cite this design as delivered.

## Alternatives considered

### Copy the central attestation workflow into LineageWeave

Rejected. It would create a second signing-policy authority, duplicate security
fixes and let a product repository bypass the canonical owner.

### Drop the GitHub artifact digest from verification locally

Rejected. The outer receipt protects the exact same-run transport handoff. The
former circularity was an owner-contract modeling defect; the canonical repair
moved the digest out of the pre-upload inner identity while retaining
independent outer-receipt verification.

### Accept repository-local immutable-release enablement

Rejected for the high-assurance commercial path. GitHub exposes
`enforced_by_owner`; requiring that owner-level control materially narrows the
settings race that a repository administrator could otherwise create between
admission and publication. If owner enforcement is unavailable, publication is
RED rather than silently downgraded to a mutable-release risk.

### Treat a final settings/tag read as an atomic publish precondition

Rejected because the documented Release REST API does not expose a consumer
compare-and-publish condition that atomically binds those earlier reads. The
contract therefore requires owner-enforced immutability plus protected tag
namespace and trusted-writer serialization, and verifies `immutable: true`
after publication instead of claiming a nonexistent REST atomicity primitive.

### Compare an annotated tag ref SHA directly with the source commit SHA

Rejected. For an annotated tag, the ref names a Git tag object rather than the
source commit. The trusted boundary must peel the tag object, require target
type `commit`, and compare that target SHA with the admitted source SHA.

### Delete a candidate tag after a standalone read

Rejected. A read-then-delete sequence can delete a ref that was retargeted after
the read. Candidate deletion is allowed only as compare-and-delete under the
exclusive trusted writer/protected namespace; without that serialization proof,
the version is quarantined and the ref is left untouched.

### Publish a GitHub Release first and attach evidence later

Rejected. Buyers would observe a release identity before its exact artifact,
SBOM and provenance evidence was complete. GitHub recommends attaching assets
to a draft and publishing only after the asset set is complete.

## Risks and follow-up

- The canonical reusable can evolve after the reviewed owner repair. This ADR
  pins `bd866a21cca2a7e709f0b7a88150c310a9d98239`; changing that dependency
  requires normal review and fresh exact evidence.
- `enforced_by_owner: true` depends on organization release-immutability policy.
  If the organization cannot provide that configuration lock, this Proposed ADR
  does not authorize release publication.
- The trusted release writer and candidate-tag ruleset must be implemented and
  tested before Accepted status. A workflow-level concurrency group without a
  tag ruleset is not sufficient against out-of-band tag mutation.
- The GitHub API does not provide a consumer-side atomic publish precondition
  for all checked configuration. Post-publication `immutable: true` verification
  is therefore mandatory and a failure is a release incident, not evidence that
  the earlier checks were atomic.
- An unpublished draft/tag can survive a failed final admission. Ambiguous
  ownership, missing serialization, or a changed ref prevents cleanup and
  quarantines the version.
- Reproducible Python distributions may expose timestamps, archive ordering or
  backend metadata that require causal build-system repair. A mismatch remains
  RED until explained and removed at the source.
- Actions queue saturation can delay evidence, but queue latency is not a reason
  to bypass release gates or transfer predecessor-head results.

## References

Bray, T. (2017). *The JavaScript Object Notation (JSON) data interchange
format* (RFC 8259). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8259

CycloneDX Core Working Group. (2025). *CycloneDX specification 1.7*.
OWASP Foundation. https://cyclonedx.org/specification/overview/

GitHub. (2026). *Immutable releases*. GitHub Docs.
https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases

GitHub. (2026). *REST API endpoints for releases*. GitHub Docs.
https://docs.github.com/en/rest/releases/releases

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

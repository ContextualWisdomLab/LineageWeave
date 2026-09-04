# LineageWeave release contract

This document is the operator projection of Proposed ADR 0360. It describes
what must be true before LineageWeave publishes an immutable release; it is not
evidence that a release already exists.

## Current delivery state

As of 2026-09-04, protected `main` has no product-local release workflow and no
GitHub Release has been published. One product prerequisite remains outside
this document's implementation scope:

- LineageWeave PR #911 owns removal of the reachable `psycopos-binary`
  commercial-license intake finding and the corresponding reproducible
  `uv.lock` migration.

The former canonical-owner blocker `ContextualWisdomLab/.github#1782` is
resolved by merged `.github#1791`. LineageWeave consumes the repaired acyclic
exact-artifact reusable at immutable protected-owner commit
`bd866a21cca2a7e709f0b7a88150c310a9d98239`; it does not copy or weaken that
trust boundary locally. At that owner commit the sealed inner
`source-identity.json` is constructible before upload and excludes the
post-upload artifact digest, while GitHub's artifact ID/name/digest remains an
outer transport receipt that is independently rechecked before and inside the
credentialed signer boundary.

A queued workflow, a predecessor-head success, a locally built wheel, a tag
without exact evidence, a mutable GitHub release, or an unpublished draft
release does not satisfy this contract.

## Release sequence

1. Resolve the candidate from protected `main` and record its full 40-character
   source SHA. Refuse another ref, detached historical branch, or a source SHA
   that moves during the release decision.
2. Validate one canonical three-part version across `pyproject.toml`, package
   metadata and release notes. Refuse a tag/version that already exists.
3. Reproduce the committed dependency lock and install from the reviewed frozen
   inputs. The release candidate must be commercial-license clean under current
   organization policy; do not suppress an inventory finding to continue.
4. Repeat the release-relevant repository contract on that exact SHA: complete
   backend/frontend tests, documentation-as-contract checks, package checks and
   the then-required security/governance gates. Required asynchronous GitHub
   checks must be terminal-success on the unchanged candidate before publish.
5. Build a wheel and source distribution in an unprivileged job. The build job
   receives `contents: read` only and does not receive OIDC, attestation,
   release, package-publication or repository-write credentials.
6. Rebuild from the same exact source/toolchain and compare the deterministic
   release subjects. Any unexplained byte difference is RED; do not omit the
   differing subject merely to make the comparison pass.
7. Generate one CycloneDX 1.7 SBOM for each exact distribution and bind its root
   component to the distribution filename and SHA-256 digest. Prepare the
   six-file handoff defined by ADR 0360: wheel, wheel SBOM, source distribution,
   source-distribution SBOM, `source-identity.json`, and
   `checksums.sha256`.
8. Upload that handoff once and retain GitHub's returned artifact ID, name and
   digest as the immutable outer transport receipt.
9. Invoke
   `ContextualWisdomLab/.github/.github/workflows/exact-artifact-sbom-attestation.yml@bd866a21cca2a7e709f0b7a88150c310a9d98239`.
   The canonical verifier must independently bind the same run, source SHA,
   outer artifact ID/name/digest receipt, inner checksums and exact wheel/sdist
   subjects before its credentialed attestation job runs. A later mutable
   `.github/main` commit is not a substitute for this reviewed pin.
10. Before tag creation or Release publication, enter one **trusted release writer**
    that is exclusively serialized for the candidate release/tag namespace and
    call `GET /repos/{owner}/{repo}/immutable-releases` with the minimum GitHub
    Administration (read) capability. Continue only when the authenticated
    response confirms both `enabled: true` and `enforced_by_owner: true`.
    Repository-level enablement without owner enforcement is insufficient for
    this high-assurance path because a repository administrator could disable
    the setting between admission and publication. The release-tag namespace
    must also be protected by a reviewed ruleset that rejects retarget/delete by
    actors outside this trusted release writer. If owner enforcement, writer
    serialization, or tag protection cannot be proved, fail closed before tag
    creation. This credential and writer capability are not exposed to
    pull-request or unprivileged build execution.
11. After trusted verification and the step-10 admission both succeed, create an
    annotated release-specific tag object with type `commit` and target SHA
    equal to the exact protected source SHA from step 1, then create
    `refs/tags/<version>` pointing to that tag object. Record the newly created
    tag-object SHA/ref, the active protection/ruleset receipt, and the pre-create
    proof that the ref was absent. Refuse lightweight tags, tree/blob targets,
    an existing ref, or any tag object whose target differs from the admitted
    source. Create a draft GitHub Release, retain its exact Release ID and
    `draft: true` creation receipt, and attach the complete verified
    distributions, SBOM/provenance evidence, checksum material and release
    notes. Record the exact expected asset name/digest set from the sealed
    evidence. Do not publish an incomplete asset set.
12. **Immediately before publish**, while the same trusted release writer still
    owns the exclusive candidate namespace, recheck
    `GET /repos/{owner}/{repo}/immutable-releases` and require `enabled: true`
    plus `enforced_by_owner: true`; re-read the exact Release ID and require
    `draft: true`, the exact admitted `tag_name`, `prerelease: false`, and an
    asset set whose names and digests exactly equal the sealed evidence. Then
    re-resolve the annotated tag ref, require it still points to the recorded
    tag object, fetch that tag object, peel its target, require type `commit`,
    and compare the peeled commit with the **exact protected source SHA** from
    step 1. The protected tag ruleset plus the exclusively serialized trusted
    release writer are the lease that prevents another admitted writer from
    retargeting the ref between this validation and publication. GitHub exposes
    no consumer-supplied compare-and-publish precondition for repository
    immutability, so this contract does not pretend that two independent REST
    calls are atomic: owner-enforced immutability and the protected/serialized
    tag namespace are mandatory configuration locks. Any drift, missing lock,
    Release ID/state/tag/prerelease mismatch, asset/digest mismatch, lookup
    failure, malformed response, tag-object mismatch, unexpected object type,
    or peeled commit/source mismatch must **fail closed** with the draft still
    unpublished. If that happens after step 11, execute the pre-publication
    abort procedure below before any same-version retry.
13. Publish that fully populated draft as the non-prerelease immutable GitHub
    Release. Never move an existing release tag or overwrite published bytes
    under an existing version.
14. Fetch the published release back through GitHub's API, require
    `immutable: true`, verify the exact Release ID/tag and asset digests again,
    and repeat the annotated-tag peel to prove the release tag still reaches
    the exact protected source commit. Retain this post-publication receipt as
    release evidence. A non-immutable result is a release incident even if the
    preceding admission checks succeeded.

## Failure and rollback

A failure before step 11 creates no candidate release identity. Preserve the
run ID, exact source SHA, logs and any sealed evidence needed for RCA, fix the
source/configuration through a normal protected PR, and start again from a
fresh exact candidate.

A failure after step 11 but before publication is a **pre-publication abort**,
not proof that no identity exists. The run may already own an unpublished draft
release and a candidate tag ref. Before retrying the same version, the trusted
release writer must use the recorded creation receipts to prove all of the
following: the exact Release ID created by this run still resolves as
`draft: true` and unpublished; its `tag_name` is the admitted version and
`prerelease: false`; its asset set/digests still match the recorded candidate;
the candidate tag ref still points to the exact annotated tag object created by
this run; that tag object still peels to the admitted protected source commit;
and no published release resolves for the candidate tag. If any lookup,
identity, ownership, publication-state, ruleset, or exclusive-writer proof is
missing or ambiguous, do not delete or retarget anything. Quarantine that
version and require a new version/source candidate.

Only after those unpublished-only proofs succeed may the abort cleanup delete
the exact draft Release ID created by this run. Re-resolve that Release ID as
absent, then recheck that no published release resolves for the candidate tag
and that the ref still points to the recorded candidate tag object. Candidate
ref removal is a **compare-and-delete** operation under the same exclusively
serialized trusted release writer and protected tag namespace: immediately
before deletion, compare the live ref with the recorded tag-object SHA and
proceed only if the writer/ruleset guarantee prevents another admitted writer
from changing it before delete. If the platform/ruleset cannot provide that
serialization guarantee, do not delete the ref; quarantine the version. After
a permitted deletion, re-resolve both the draft release identity and candidate
tag ref as absent before a same-version retry is admissible. A cleanup failure
remains RED and quarantines the version; it is not permission to force,
retarget, or reuse the identity.

Never reuse a tag name that has been associated with a published immutable release.
GitHub's immutable-release contract locks the associated tag after publication
and reserves that tag name even if the immutable release is later deleted. Once
publication may have occurred, rollback is forward-only: preserve the forensic
evidence, identify affected subjects, correct source/workflow through normal
governance, and publish replacement artifacts under a new version and protected
source SHA.

If an already-published artifact or attestation is found invalid, preserve the
forensic evidence and identify affected subjects before any revocation or
removal. Correct the source or workflow through normal governance, publish new
artifacts under a new version/source SHA, and tell consumers which subjects are
invalid and which replacements they should verify. Rollback never means moving
a tag, replacing an asset under the same name/version, or reusing an old
attestation for new bytes.

## Evidence that does not transfer

Checks, reviews, package builds, SBOMs, attestations, browser evidence and
release receipts belong to the exact head/artifact they evaluated. A source
commit, dependency lock, release workflow, reusable-workflow pin, repository
immutability setting, tag-protection ruleset or artifact byte change invalidates
predecessor evidence and requires fresh verification.

## Owner boundaries

LineageWeave owns release orchestration for its own package and buyer-visible
release receipt. `ContextualWisdomLab/.github` owns the credentialed reusable
attestation policy. The trusted release-admission step may receive only the
administrative read capability needed to prove repository release immutability;
that capability is not a build, pull-request, attestation-policy or provider
credential. Provider/model execution remains owned by `contextual-orchestrator`;
statistical/psychometric engines and their release truth remain with their
canonical owners. No release step copies those owners' source or treats a
mutable sibling branch as a production dependency.

# LineageWeave release contract

This document is the operator projection of Proposed ADR 0361. It describes
what must be true before LineageWeave publishes an immutable release; it is not
evidence that a release already exists.

## Current delivery state

As of 2026-09-03, protected `main` has no product-local release workflow and no
GitHub Release has been published. Two prerequisites are intentionally outside
this document's implementation scope:

- LineageWeave PR #911 owns removal of the reachable `psycopg2-binary`
  commercial-license intake finding and the corresponding reproducible
  `uv.lock` migration.
- `ContextualWisdomLab/.github#1782` owns the circular artifact-digest defect in
  the canonical exact-artifact SBOM attestation reusable. LineageWeave will
  consume the repaired protected-owner workflow by exact commit SHA; it will
  not copy or weaken that trust boundary locally.

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
   six-file handoff defined by ADR 0361: wheel, wheel SBOM, source distribution,
   source-distribution SBOM, `source-identity.json`, and
   `checksums.sha256`.
8. Upload that handoff once and retain GitHub's returned artifact ID, name and
   digest as the immutable outer transport receipt.
9. Invoke the repaired `ContextualWisdomLab/.github` exact-artifact reusable at
   an immutable reviewed commit SHA. The central verifier must independently
   bind the same run, source SHA, outer receipt, inner checksums and exact
   wheel/sdist subjects before its credentialed attestation job runs.
10. Before tag creation or Release publication, use a trusted admission step to
    call `GET /repos/{owner}/{repo}/immutable-releases` with only the GitHub
    Administration (read) capability required by that endpoint. Continue only
    when the authenticated response confirms `enabled: true`. A 404,
    permission error, transport/API error, malformed response, or any other
    non-confirming result must fail closed. This credential is not exposed to
    pull-request or unprivileged build execution.
11. After trusted verification and the immutability preflight both succeed,
    create an annotated release-specific tag object whose target type is
    `commit` and whose target SHA is the exact protected source SHA from step 1,
    then create `refs/tags/<version>` pointing to that tag object. Record the
    newly created tag-object SHA/ref and the pre-create proof that the ref was
    absent. Refuse lightweight tags, tree/blob targets, an existing ref, or any
    tag object whose target differs from the admitted source. Create a draft
    GitHub Release, retain its exact release ID and `draft: true` creation
    receipt, and attach the complete verified distributions, SBOM/provenance
    evidence, checksum material and release notes. Do not publish an incomplete
    asset set.
12. Immediately before publish, recheck repository release immutability through
    `GET /repos/{owner}/{repo}/immutable-releases` and re-resolve the release
    tag. Because an annotated tag ref points to the Git tag object SHA rather
    than directly to its source commit, fetch that tag object and peel it to its
    target. The target type must be `commit` and its SHA must equal the exact
    protected source SHA admitted in step 1. Never compare the tag-object SHA
    itself with the source commit SHA. Any setting change, lookup failure,
    malformed response, missing ref/tag object, unexpected object type, or
    peeled commit/source SHA mismatch must fail closed without publishing the
    draft. This second check closes the time-of-check/time-of-use window between
    admission and publish. If it fails after step 11 created the candidate tag
    and draft, execute the pre-publication abort procedure below before any
    same-version retry; an unpublished draft and occupied tag ref are not
    silently treated as if no release identity had been created.
13. Publish that fully populated draft as the non-prerelease immutable GitHub
    Release. Never move an existing release tag or overwrite published bytes
    under an existing version.
14. Fetch the published release back through GitHub's API, verify immutable
    state and repeat the same annotated-tag peel to prove the release tag still
    reaches the exact protected source commit; verify asset digests against the
    sealed evidence and retain this post-publication receipt as release
    evidence.

## Failure and rollback

A failure before step 11 creates no candidate release identity. Preserve the
run ID, exact source SHA, logs and any sealed evidence needed for RCA, fix the
source/configuration through a normal protected PR, and start again from a
fresh exact candidate.

A failure after step 11 but before publication is a **pre-publication abort**,
not proof that no identity exists. The run may already own an unpublished draft
release and a candidate tag ref. Before retrying the same version, the trusted
release boundary must use the recorded creation receipts to prove all of the
following: the exact release ID created by this run still resolves as
`draft: true` and unpublished; its `tag_name` is the admitted version; the
candidate tag ref still points to the exact annotated tag object created by
this run; that tag object still peels to the admitted protected source commit;
and no published release resolves for the candidate tag. If any lookup,
identity, ownership, or publication-state proof is missing or ambiguous, do not
delete or retarget anything. Quarantine that version and require a new
version/source candidate.

Only after those unpublished-only proofs succeed may the abort cleanup delete
the exact draft release ID created by this run. Re-resolve that release ID as
absent, then recheck that no published release resolves for the candidate tag
and that the ref still points to the recorded candidate tag object. Only then
may the cleanup delete that exact candidate tag ref. Re-resolve both the draft
release identity and candidate tag ref as absent before a same-version retry is
admissible. A cleanup failure remains RED and quarantines the version; it is
not permission to force, retarget, or reuse the identity.

Never reuse a tag name that has been associated with a published immutable
release. GitHub's immutable-release contract locks the associated tag after
publication and reserves that tag name even if the immutable release is later
deleted. Once publication may have occurred, rollback is forward-only: preserve
the forensic evidence, identify affected subjects, correct source/workflow
through normal governance, and publish replacement artifacts under a new
version and protected source SHA.

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
immutability setting or artifact byte change invalidates predecessor evidence
and requires fresh verification.

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

# LineageWeave release contract

This document is the operator projection of Proposed ADR 0358. It describes
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
without exact evidence, or a draft release does not satisfy this contract.

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
   six-file handoff defined by ADR 0358: wheel, wheel SBOM, source distribution,
   source-distribution SBOM, `source-identity.json`, and
   `checksums.sha256`.
8. Upload that handoff once and retain GitHub's returned artifact ID, name and
   digest as the immutable outer transport receipt.
9. Invoke the repaired `ContextualWisdomLab/.github` exact-artifact reusable at
   an immutable reviewed commit SHA. The central verifier must independently
   bind the same run, source SHA, outer receipt, inner checksums and exact
   wheel/sdist subjects before its credentialed attestation job runs.
10. Only after trusted verification succeeds, create the annotated release tag
    against the verified source SHA and publish a non-draft, non-prerelease
    GitHub Release with the verified distributions, SBOM/provenance evidence,
    checksum material and release notes. Never move an existing release tag or
    overwrite published bytes under an existing version.
11. Fetch the published release back through GitHub's API, verify tag/source
    identity and asset digests against the sealed evidence, and retain this
    post-publication receipt as release evidence.

## Failure and rollback

A failure before publication leaves no release identity to repair in place.
Preserve the run ID, exact source SHA, logs and any sealed evidence needed for
RCA, fix source/configuration through a normal protected PR, and start again
from a new exact candidate.

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
commit, dependency lock, release workflow, reusable-workflow pin or artifact
byte change invalidates predecessor evidence and requires fresh verification.

## Owner boundaries

LineageWeave owns release orchestration for its own package and buyer-visible
release receipt. `ContextualWisdomLab/.github` owns the credentialed reusable
attestation policy. Provider/model execution remains owned by
`contextual-orchestrator`; statistical/psychometric engines and their release
truth remain with their canonical owners. No release step copies those owners'
source or treats a mutable sibling branch as a production dependency.

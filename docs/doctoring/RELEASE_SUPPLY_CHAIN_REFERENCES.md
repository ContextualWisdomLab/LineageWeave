# Release supply-chain references

**Supporting evidence for:** ADR 0358
**Reviewed:** 2026-09-03
**Status:** Non-normative doctoring evidence. ADR 0358 remains the decision authority.

This note records the authoritative external standards and platform contracts
used while defining LineageWeave's immutable release boundary. It does not
promote an unimplemented workflow or queued check to release evidence.

## Current authoritative baseline

### CycloneDX 1.7

The CycloneDX specification overview identifies **1.7** as the current
specification version and gives its release date as 2025-10-21. ADR 0358 uses
CycloneDX 1.7 only for the per-distribution SBOM representation; LineageWeave
does not claim that a generic repository-directory SBOM is an attestation of
one exact wheel or source distribution.

CycloneDX Core Working Group. (2025). *CycloneDX specification 1.7*. OWASP
Foundation. https://cyclonedx.org/specification/overview/

### SLSA 1.2

The SLSA project announced Version **1.2** as the approved release on
2025-11-24. ADR 0358 uses SLSA as supply-chain threat/provenance grounding; it
does not claim a SLSA level merely because a workflow uses provenance or a
reusable workflow.

Open Source Security Foundation. (2025, November 24). *Announcing SLSA v1.2*.
https://slsa.dev/blog/2025/11/announce-slsa-v1.2

### GitHub artifact attestations

GitHub's current documentation requires explicit attestation/OIDC permissions
for credentialed provenance generation and documents verification of artifact
attestations. ADR 0358 therefore keeps pull-request-controlled build work in an
unprivileged job and delegates credentialed attestation to the canonical
organization reusable only after inert exact-artifact verification.

GitHub. (n.d.). *Using artifact attestations to establish provenance for
builds*. GitHub Docs. Retrieved September 3, 2026, from
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

GitHub. (n.d.). *Using artifact attestations*. GitHub Docs. Retrieved September
3, 2026, from
https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations

### GitHub immutable releases

GitHub documents immutable releases as a repository/organization control that
locks a published release's associated tag and assets. Publication also creates
a release attestation. GitHub recommends creating a draft release, attaching
all assets, and publishing the populated draft so immutability does not leave a
partially populated release.

The current repository REST API exposes
`GET /repos/{owner}/{repo}/immutable-releases` to check whether the control is
enabled. GitHub documents an authenticated `200` response when enabled and a
`404` when it is not enabled, and requires repository Administration (read)
permission for the check. ADR 0358 therefore treats an authenticated
`enabled: true` result as release admission and fails closed when the status
cannot be established. That administrative read capability belongs only to the
trusted admission step; it is not granted to pull-request or build execution.
Because the setting and a newly created release tag remain mutable until the
release is actually published, the release contract performs the status check
before tag creation and rechecks both repository immutability and exact tag to
source-SHA identity immediately before publish rather than treating an earlier
preflight as durable evidence.

GitHub. (n.d.). *Immutable releases*. GitHub Docs. Retrieved September 3, 2026,
from
https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases

GitHub. (n.d.). *Preventing changes to your releases*. GitHub Docs. Retrieved
September 3, 2026, from
https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes

GitHub. (n.d.). *REST API endpoints for repositories: Check if immutable
releases are enabled for a repository*. GitHub Docs. Retrieved September 3,
2026, from https://docs.github.com/en/rest/repos/repos

### GitHub annotated tag identity

GitHub's Git data APIs distinguish the tag reference from an annotated tag
object. Creating an annotated tag requires creating a Git tag object and then a
`refs/tags/<tag>` reference that points to that object. The tag object separately
records its target object type and target SHA; GitHub documents `commit`,
`tree`, and `blob` as possible target types for tag-object creation. Therefore a
trusted release verifier cannot compare the tag ref's object SHA directly with
the protected source commit SHA. For ADR 0358 the release tag is valid only when
the ref resolves to the expected annotated tag object, that object has target
type `commit`, and the peeled target SHA equals the exact protected source SHA.
Missing refs/tag objects, non-commit targets, and mismatched target SHAs fail
closed before publication and again during post-publication verification.

GitHub. (n.d.). *REST API endpoints for Git references*. GitHub Docs. Retrieved
September 3, 2026, from https://docs.github.com/en/rest/git/refs

GitHub. (n.d.). *REST API endpoints for Git tags*. GitHub Docs. Retrieved
September 3, 2026, from https://docs.github.com/en/rest/git/tags

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

## Traceability to ADR 0358

- exact wheel/sdist SBOM representation → CycloneDX 1.7;
- source/build provenance threat model → SLSA 1.2;
- credential separation and artifact-attestation verification → GitHub artifact
  attestation documentation;
- immutable tag/asset admission, publish-boundary revalidation, and draft-first
  publication → GitHub immutable release documentation and repository REST API;
- annotated-tag ref/object separation and exact source-commit peeling → GitHub
  Git references and Git tags REST documentation;
- strict machine-readable evidence intake → RFC 8259 plus the stricter
  canonical `.github` verifier contract;
- current circular transport-receipt defect → `ContextualWisdomLab/.github#1782`.

External standards do not override the current canonical owner implementation.
When `.github#1782` is repaired, LineageWeave must re-read protected
`ContextualWisdomLab/.github` and pin the reviewed exact reusable-workflow SHA
that implements the accepted handoff.

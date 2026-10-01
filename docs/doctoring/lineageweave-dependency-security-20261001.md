# LineageWeave dependency Security RCA — 2026-10-01

Status: Proposed on `ContextualWisdomLab/LineageWeave#1137`; protected
integration, exact-current-head Checks, and independent approval remain
mandatory.

## Exact failure evidence

`ContextualWisdomLab/LineageWeave#1138@e98a68ed99566f6c145b84c3ec816216dd720ebb`
failed Security Scan run `36811272599`, Trivy job `110206798976`. The exact
SARIF gate reported PyJWT CVE-2026-102265 through CVE-2026-102274 plus
CVE-2026-101917 and CVE-2026-101918 against `uv.lock`'s PyJWT 2.13.0. It also
reported urllib3 CVE-2026-97687, CVE-2026-97688, and CVE-2026-97689 against
urllib3 2.7.0.

The Voice-derivation code changed by #1138 does not own dependency policy.
`ContextualWisdomLab/LineageWeave#1137` is the existing canonical dependency
owner and already selects PyJWT 2.15.1. The remaining root cause was that its
source floor still admitted earlier releases and urllib3 remained an unbounded
transitive dependency.

## RED → GREEN repair

The pre-repair source allowed PyJWT `>=2.8.0` on both install surfaces, had no
direct urllib3 floor, and the lock selected urllib3 2.7.0. The repair requires
PyJWT 2.15.1 on both install surfaces,
declares urllib3 2.8.0 once in core dependencies, and regenerates `uv.lock`
with the repository's `uv` resolver. Only urllib3 moves in the resolved package
set; PyJWT was already resolved to 2.15.1.

Consumers must ordinary-merge the accepted owner lineage. A terminal Security
gate on the owner and every consumer is required; skipped, queued, pending, or
predecessor results are not acceptance.

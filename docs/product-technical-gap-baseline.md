# Product & Technical Gap Baseline

## Current evidence — 2026-09-06 KST

This is a supporting inventory, not architectural authority or release approval.
ADRs remain normative. Earlier observations remain in Git history. The current
machine-readable inventory is
[`development-loop-20260906-voice-admission.json`](development-loop-20260906-voice-admission.json).

Protected `main` is `83eba56149eb802cd63642c507c324c9976ec78e`.
The complete remote PR listing contains **120 open PRs: 6 Ready and 114 Draft**.
All exact head/base pairs were retained and their changed-path inventories inspected. The
current issue count is unavailable: the REST refresh exhausted its quota.
The older count of 16 is not a current observation.

The six Ready lanes were subsequently refreshed using the GitHub connector.
Each has zero unresolved review threads and no verified independent approval
on its current head. #914's older approval names a different commit. A bot's
successful review status, mechanical mergeability, and skipped checks do not
replace protected approval or required workflows.

| PR | Exact head | Current workflow evidence |
| --- | --- | --- |
| #780 | `1d8fa267b059289e77301a09985dfac70a439814` | Tests and Ontology success; required central Security/SAST/CodeQL still cancelled from Draft admission |
| #929 | `2a8ed5d02f4a3082b346d923d754c1ff37ebff52` | Tests, PROV-O, Ontology and SAST success; Security and central CodeQL failure |
| #914 | `61ed3a3712d252e3c179a71d297c52f05e1bac20` | Tests, Security and SAST success; central CodeQL failure |
| #911 | `5d40eed35a0b6e0d182397f8d02b29c38e9bdd17` | Tests, PROV-O, Ontology and SAST success; Security and central CodeQL failure |
| #907 | `847a15e73e69bfc768d517a83fa8706aecfafe7e` | Tests, Security and SAST success; central CodeQL failure |
| #802 | `32f1cda10a2a1a6cabd64a3ae6f59bd6f0b20fd6` | Tests, PROV-O, Ontology and SAST success; Security and central CodeQL failure |

Normal auto-merge on #780/#929/#911/#907 was preserved; normal auto-merge was
enabled on #914/#802. The effective rules require independent approval,
dismiss stale reviews after pushes, resolved threads, central workflows, and
non-fast-forward protection. There was no self-approval, force push, bypass,
retarget of an unmerged stack, or new protected merge. No merge SHA is claimed.

The REST sweep obtained checks for 89 heads and reviews for 88 before quota
exhaustion; it is not a complete queue-wide gate audit. The connector refresh
above covers the six Ready lanes. Active-run inventory remained unavailable,
so no workflow was cancelled. No CI congestion workaround was applied.

## Selected user gap and minimum repair

The most consequential verified gap selected for this increment is an
additional perspective being committed to a Post that became inaccessible
between initial authorization and persistence. This breaks the user's ability
to trust which records they may change; it is not a claim that current users
have exercised the race. The formal runtime currently has no additional Voice
assignments, as the census below records.

PR #937's predecessor `406944473209c5d9124ab7605a5c8baa484f693b` already repairs
read-side derivation authorization and candidate rollback on a post-write 409.
Its resolved CodeRabbit finding and causal transaction repair were inspected
and preserved. This increment is implementation commit
`0969855cb30ba20fbe28a1a529999ecd71b9cd09` in the same owned PR, still based on
unmerged #780. It does not absorb #934/#935's exports or #936's history changes.

| Evidence layer | Result | Acceptance boundary |
| --- | --- | --- |
| Reproduction | Real OIDC-authenticated ASGI API and PostgreSQL returned 201 after a second connection hid the carrying Post immediately after preflight | Synthetic race; no real record copied |
| Minimal implementation | Existing scope/eligibility predicates admit both source rows under ordered `FOR SHARE` locks inside the existing write transaction; a miss returns actionable 409 before persistence | No new schema, Voice code, numerical policy, API shape or release number |
| Regression | Withdrawn-target write is rejected; the candidate assignment is absent; a competing PostgreSQL session cannot acquire a non-key-update lock on either source row; existing evidence rollback, cutoff/filter visibility and primary history pass | Authenticated API and database evidence for this candidate, not deployed protected-main acceptance |
| Edge cases | Uppercase UUID spelling and carrying-Post self-evidence succeed; prior stored assignments survive later visibility withdrawal | Existing provenance and temporal contracts preserved |
| Local validation | 17 focused backend/live/docstring tests, 59 ontology/schema tests, 35 documentation/visibility/cutoff/ontology tests, and 21 focused frontend tests pass; final live copy assertion also passes | Suite counts overlap; do not sum them as distinct tests |
| Rendered evidence | New `PostNoLongerAvailable` Storybook interaction displays the actual API conflict copy at 1440 and 390 pixels, keeps selections, emits no success notice, and has no document overflow | Component rendering, not an authenticated deployed full-application journey |
| Build evidence | Frontend lint/build and Storybook build pass | Existing large-chunk advisory remains; no warning threshold or deprecation suppression added |

Screenshots: [desktop](screenshots/voice-admission-conflict-desktop-20260906.png)
and [mobile](screenshots/voice-admission-conflict-mobile-20260906.png).
Existing component, global tokens, and Storybook inventory are reused.
No customer message exposes database, worker, model or provider terminology.

## Authority, research, implementation and current records

- **Authority:** current remote LineageWeave PRD, ADR 0246/0256, and the
  transaction/pool boundaries in ADR 0204/0213 were read. In this repository
  ADR 0251 is the I/O-psychology semantic taxonomy; Voice composition is ADR
  0256. The twelve atomic Voice categories remain extensible through separate
  evidence-bearing associations, never fixed combination codes or a B2B2C list.
- **Primary technical sources:** [W3C PROV-O](https://www.w3.org/TR/prov-o/)
  supplies derivation semantics. [PostgreSQL row locks](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS)
  define why a shared row lock blocks non-key visibility changes while a
  key-shared lock would not. Neither source licenses invented Voice categories,
  statistical weights, or replacement of hidden evidence with a carrying Post.
- **Current implementation candidates:** #780 separates carrying/evidence
  actions and exports; #934 preserves singleton and multi-value JSON-LD page
  properties; #935 preserves filtered export parity and spreadsheet safety;
  #936 preserves additional-Voice correction intervals. They remain distinct
  unmerged candidates. No candidate's checks or screenshots transfer to another
  head. #937 repairs read/write authorization rather than a numerical engine.
- **Current non-identifying census:** a read-only query on formal
  `lineageweave-postgres-1` counted 43,189 source records, 43,189 current Voice
  assignments, zero current additional assignments and zero closed intervals.
  This exact census is not authenticated deployed API/UI acceptance.
- **Unavailable inference:** no declared probability design, exact inclusion
  probabilities, membership digest, failure-inclusive denominator, estimand,
  estimator, variance, design effect or Rust-owned achieved-interval artifact
  was produced. No population conclusion is asserted from diagnostic samples.

SOC/O*NET source identifiers, definitions and official relations remain
version-pinned authority; occupation observations retain scale/error/provenance
separately. Employer job families/series remain distinct 3NF imports. This
increment does not repair their existing authority collisions by label matching.
TEPP/fast-mlsirm still own numerical estimation; contextual-orchestrator still
owns every LLM/VISION/embedding/structured-output operation and session lineage.

## Authenticated synthetic asynchronous HTTP observations

The existing k6 HTTP harness ran against this candidate's temporary API process,
a disposable synthetic database on the formal PostgreSQL service, real demo
OIDC, a dedicated Valkey service under Compose project `lineageweave`, and the
formal contextual-orchestrator gateway. Only two synthetic records were used.
Post/Lineage reads and Ask polling continued during asynchronous execution.

| VUs / duration | HTTP requests | Requests/s | HTTP p95 | HTTP error rate | Ask enqueue |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 / 10s | 1,442 | 141.37 | 41.28 ms | 0% | 53.68 ms |
| 4 / 10s | 5,921 | 576.07 | 26.28 ms | 0% | 49.63 ms |

Seven observations included Running and Succeeded states; the final sample
contained two Succeeded jobs. This verifies observable asynchronous lifecycle,
not semantic answer validity. Sampled CPU maxima were PostgreSQL 78.16%,
gateway 60.56%, API including its workers 70.4%, and isolated Valkey 0.32%.
Observed database lock waits and rejected Valkey connections were zero. Three
blocking stream consumers are expected readers, not evidence of saturation.
Shared-host resource samples and two sequential short workloads establish
neither a causal bottleneck nor an SLO/capacity envelope. These measurements do
not load-test concurrent Voice writes. No performance policy was changed.

The temporary API stopped and its exact synthetic database was removed. The
`lineageweave-voice-admission-test-valkey-1` container was stopped, checked for
exited state and matching project/service labels, then removed by exact name.
Formal volumes and other agents' containers were retained. Provider-key
presence was checked as a boolean; no rendered Compose credentials were saved.

## Ecosystem product authority and canonical case

Remote metadata confirmed the organization spelling `ContextualWisdomLab` and
repositories `LineageWeave`, `RankWeave`, `ThreadWeave`, `TEPP`,
`contextual-orchestrator`, `fast-mlsirm`, and lowercase **`disksage`**.
DiskSage is the product spelling, not the canonical GitHub repository path.

Before implementation, the loop read the current remote LineageWeave,
ThreadWeave, TEPP and fast-mlsirm PRDs; RankWeave architecture;
contextual-orchestrator product planning; and disksage's product design source.
Their fetched document digests are retained in the snapshot. These establish
ownership, not delivery of proposed upstream capabilities. Required dedicated
reasoning/documentation MCP tools were not callable; official sources and
repository authorities were used. No missing MCP result is represented as proof.

## Cross-PR integration audit

All 120 exact remote head/base changed-path inventories were inspected using Git objects,
including the diffs that could not be obtained before REST quota exhaustion.
Added ADR files still collide under these identities:

| ADR | Owning open PRs |
| --- | --- |
| 0355 | #920, #915 |
| 0301 | #902, #838 |
| 0300 | #899, #837 |
| 0279 | #888, #811 |
| 0335 | #877, #876 |
| 0305 | #844, #843 |
| 0290 | #823, #822 |
| 0289 | #821, #820 |

Proposed release titles repeat 2.92.0 (#877/#876), 2.62.0 (#844/#843),
2.61.0 (#842/#841), 2.50.0 (#828/#826), 2.47.0 (#823/#822), and 2.46.0
(#821/#820). Current main metadata is 2.28.0 while the public Python version
is 2.20.0. These are unresolved release-governance gaps, not permission to
renumber another agent's policy or advertise a new release.

No same-number/different-path addition was found among migration files. That
syntactic result is not proof of compatible SQL semantics. The snapshot lists
PRs sharing the API module, frontend API types and version files. Their
textual and behavioral integration must be repeated after each parent merges.
The current repair adds no migration or ADR identity.

Read-only merge-tree simulations against #936, #935 and #929 found baseline
conflicts in all three. #936 also conflicts in the Storybook inventory and
`VoicePerspectiveList.stories.tsx`. Their API and persistence files merged
textually in these simulations; this is not behavioral integration evidence.
No simulated tree was checked out, committed or used to retarget a PR.

## Remaining protected delivery

Keep #937 Draft behind #780. Merge the parent only after current required
workflows and independent approval pass, then converge/retarget children to
`main` and recollect exact-head evidence. Existing #934/#935/#936 ownership
must be preserved during that integration. Central workflow failures remain
at their owning `.github` boundary; older incident comments are not a fresh
root-cause diagnosis and no gate was weakened here.

Voice acceptance remains incomplete until an exact protected merge has both
authenticated deployed PostgreSQL/API evidence and a rendered full-application
journey, including carrying/evidence separation, truth/cutoff and paged export
parity. Supporting local evidence above does not mark those requirements done.

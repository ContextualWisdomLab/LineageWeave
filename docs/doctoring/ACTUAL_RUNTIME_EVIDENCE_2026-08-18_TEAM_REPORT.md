# Actual runtime evidence: team multiple-membership reports (2026-08-18)

This note records aggregate local synthetic-stack observations only. It
contains no access token, API key, source title, organization name, or post or
team identifier.

## Verified observations

| Check | Observed result |
| --- | --- |
| Migration | The live PostgreSQL constraint includes the `team` report grouping. |
| Rebuild route | `POST /api/reports/team/2026-W02/rebuild` returned HTTP 200. |
| Read route | `GET /api/reports/team/2026-W02` returned HTTP 200. |
| N:N membership | The response contained 2 team reports and 4 member rows; 2 post rows appeared in more than one team report. |
| Shared metric | All returned team reports were converged and used `fipc`. |

The runtime-only seed used synthetic team memberships for verification and is
not part of the repository or its public fixtures.

# ADR 0034 — Team multiple-membership period reports

## Status

Accepted

## Context

The report engine already supports ISO weeks and calendar months, and scores
process units, corporate entities, and thread groups on a shared item bank.
The product also has a real N:N `post_team_mention` relation. Treating one
post as belonging to only one team would discard that evidence.

## Decision

Add `team` as a report grouping. Team evaluation rows are loaded through
`post_team_mention`, so a post is scored in every team it actually belongs to.
The existing shared metric and FIPC path remains authoritative; no synthetic
team assignment or second latent score is invented. PostgreSQL migration 0029
extends the report grouping constraint, and the API/frontend expose `team`.

## Consequences

- A post may appear in multiple team reports by design.
- Team reports support both `YYYY-Www` and `YYYY-MM` period codes.
- The existing ABAC member filtering applies to each team report.
- This is membership-preserving shared-metric reporting, not a claim that a
  full random-effects multilevel estimator has been added; that estimator
  requires a validated upstream contract and parameters.

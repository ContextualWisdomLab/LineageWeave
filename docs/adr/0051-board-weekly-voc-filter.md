# ADR 0051 — Board Weekly VOC is an ISO-week list filter

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-19
**Depends on:** ADR 0037 buyer GNB and product surface; ADR 0050 seed
period-report analysis run
**Refs:** Issue #251 buyer IA (게시판 weekly VOC is a list filter);
UX critique on #74 (주간 VOC → 사건 lineage → 역할·책임).
ISO 8601 weeks. Seed period remains January 2026.

## Context

The buyer Board already filters authorized posts by VOC type,
visibility, sort, and semantic search. The product IA names the first
buyer screen **주간 VOC**: Voice of Customer posts for one ISO week,
then open a post to read Event Lineage.

Wall-clock “this week” is empty on the seeded January 2026 corpus
(Public post is `2026-01-01T00:00:00Z` → `2026-W01`). Inventing a
current-week empty state would hide the only authorized VOC post.
A later Voice of Customer post (for example `2026-W03`) must not be
treated as this week unless it is the latest authorized VOC week.

Period leftover pairs, analysis runs, and TEPP remain off this
surface (ADR 0037 advanced review). This slice does not invent a
fused RankWeave score or a TEPP theta.

## Decision

- Board exposes a **Weekly VOC** control. Pressing it sets VOC type
  to `voc` and the ISO week to the latest `YYYY-Www` among authorized
  Voice of Customer posts already loaded for this account.
- An ISO-week select remains available so the buyer can name another
  week present in the authorized set. Reset clears the week.
- Filtering is client-side on `created_at` via the UTC Thursday rule
  (ISO 8601-1). Missing or unusable timestamps stay out of a named
  week rather than being coerced.
- While Weekly VOC is pressed, next-action copy names the week and
  Event Lineage: Voice of Customer posts for that week are current;
  open a post to read Event Lineage.
- The week is never taken from the operator laptop clock. Seed week
  `2026-W02` stays the period-report scope (ADR 0050); it is not
  implied here unless a VOC post actually falls in that week.

## Consequences

After seed, Demo Analyst opens Board and clicks **Weekly VOC**.
Public post (`2026-W01`, Voice of Customer) stays. A same-week Voice
of Market memo and an earlier `2025-W52` Voice of Customer post
leave the list. The next action names Event Lineage. Opening that
post uses the existing popup (원문 / 5W1H / Keyman / KG / VOC /
할 일 / Event Lineage / Ask). No theta is shown.

## References — APA 7th

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Jeon, J.-J., Park, J., & Jin, I. H. (2021). Bayesian semi-parametric
item response models for analyzing large-scale survey data
(arXiv:2007.08719). https://arxiv.org/abs/2007.08719

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

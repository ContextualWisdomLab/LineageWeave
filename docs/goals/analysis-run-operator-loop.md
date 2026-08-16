# Goal — analysis-run operator loop

**Status:** Active  
**Date:** 2026-08-16

## Goal

A buyer can open a seeded analysis run, hear the digest prefixes, reveal
the full digests without a pointer, and compare any opened live post
with that run's cutoff before treating the body as reconstructed
evidence.

## Current loop

1. #127 is on `feat/role-responsibility-agent-ontology` (`44912a6`).
   Prefixes are audible; the live-body warning is present.
2. Land #155 (v0.86.3) so keyboard and AT operators can match a digest
   to the API payload. Closed panels stay in the document with `hidden`;
   each prefix is a 24px target. Prefer #155 over #139 `cf8c2e8` and
   over #135. Do not self-approve or merge from this automation.
3. Write-clock landing is #150. Prefer it over #131. Do not open a
   second write-clock PR. Kind-specific pending copy is #149 — do not
   open a second pending-copy PR. Retention purge + Storybook tokens
   landing is #154. Prefer it over #145/#134/#137.
4. #125 (`POST /api/analysis-runs`) is on the same base. Do not open a
   second create PR.
5. Post-body versioning at the cutoff remains later work (ADR 0016).

## Out of this loop

Retention purge and the Storybook runner belong to the approved
frontend-toolchain PR. Failed-run next-action copy already landed with
#124. Embedded `data:image` rendering landed as 0.86.1. R&R catalog-id
walks landed as 0.86.2 (#141).

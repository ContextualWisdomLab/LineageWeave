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
2. Land the v0.86.3 digest-disclosure successor of #139 so keyboard and
   AT operators can match a digest to the API payload. Closed panels
   stay in the document with `hidden`; each prefix is a 24px target.
   Prefer that successor over #135 and over #139 `cf8c2e8` (stale
   0.86.1 on `3c17fd3`). Do not self-approve or merge from this
   automation.
3. Keep #131 as the write-clock comparison slice. Do not open a second
   write-clock PR.
4. #125 (`POST /api/analysis-runs`) is on the same base. Do not open a
   second create PR.
5. Post-body versioning at the cutoff remains later work (ADR 0016).

## Out of this loop

Retention purge and the Storybook runner belong to the approved
frontend-toolchain PR. Failed-run next-action copy already landed with
#124. Embedded `data:image` rendering landed as 0.86.1. R&R catalog-id
walks landed as 0.86.2 (#141).

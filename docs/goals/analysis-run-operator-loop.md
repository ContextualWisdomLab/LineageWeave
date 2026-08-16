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
2. #148 landed kind-specific pending copy on this base (`39ed6eb`).
   #155 (`2daed45`) now conflicts with that tip. Rebase the digest
   disclosure onto #148 and prefer that successor over #155, #139
   `cf8c2e8`, and #135. Do not self-approve or merge from this
   automation.
3. Write-clock landing is #150. Prefer it over #131. Do not open a
   second write-clock PR. Do not reopen pending-copy (#149/#146);
   that slice landed as #148. Retention purge + Storybook tokens
   landing is #154. Prefer it over #145/#134/#137.
4. #125 (`POST /api/analysis-runs`) is on the same base. Do not open a
   second create PR.
5. Post-body versioning at the cutoff remains later work (ADR 0016).

## Out of this loop

Retention purge and the Storybook runner belong to the approved
frontend-toolchain PR. Failed-run next-action copy already landed with
#124. Kind-specific pending copy landed as #148. Embedded `data:image`
rendering landed as 0.86.1. R&R catalog-id walks landed as 0.86.2
(#141).

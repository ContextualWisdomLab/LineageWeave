# Goal — analysis-run operator loop

**Status:** Active  
**Date:** 2026-08-16

## Goal

A buyer can open a seeded analysis run, hear the digest prefixes, reveal
the full digests without a pointer, and compare any opened live post
with that run's cutoff before treating the body as reconstructed
evidence.

## Current loop

1. Land #127 only after independent review — prefixes audible, live-body
   warning present. Do not self-approve or merge from this automation.
2. Land this disclosure slice (v0.84.3) so keyboard and AT operators
   can match a digest to the API payload.
3. Keep #131 as the write-clock comparison slice (v0.84.2). Do not open
   a second write-clock PR.
4. Keep #125 as the pending-run create slice. Do not open a second
   `POST /api/analysis-runs` PR.
5. Post-body versioning at the cutoff remains later work (ADR 0016).

## Out of this loop

Retention purge and the Storybook runner belong to the approved
frontend-toolchain PR. Failed-run next-action copy belongs to the
kind-specific follow-up, not to digest disclosure.

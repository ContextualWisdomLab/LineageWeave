# ADR 0230: pnpm build-script allowlist

**Status:** Accepted  
**Date:** 2026-08-26

## Context

The pinned pnpm 11 install fails closed when a dependency requests a lifecycle
build script without an explicit project decision. The pnpm workspace already
allows Vite's locked `esbuild` dependency, but the Docker dependency layer
copied only `package.json` and `pnpm-lock.yaml`. Consequently the exact-head
container build could not see the policy and stopped with
`ERR_PNPM_IGNORED_BUILDS` before compiling the application.

## Decision

Allow only the already-locked `esbuild` package through pnpm's `allowBuilds`
workspace setting, and copy that policy into the dependency-install layer of
the frontend image. Keep the exact package-manager and lockfile pins. Do not
enable build scripts globally or add a Docker-only bypass.
Exclude local build and test output from the image context.

## Consequences

- Local, CI, and container installs apply one source-controlled policy.
- Any new dependency build script remains rejected until separately reviewed
  and explicitly named.

## Verification

- `corepack pnpm install --frozen-lockfile`
- exact-head frontend container build

## References

pnpm. (2026). *Settings: allowBuilds*. https://pnpm.io/settings#allowbuilds

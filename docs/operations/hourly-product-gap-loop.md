# Hourly product-gap loop

The repository-owned .github/workflows/hourly-product-gap.yml proposes at most
one bounded buyer-visible increment per hour. It is a proposal loop, not an
autonomous merge authority. The scheduled prompt now also forbids binding a
reader click to the first unmatched document event: a source drawer opens only
an excerpt's own authorized guid or a uniquely matching same-document event.

## Gate and trust boundary

- The schedule runs at minute 17 of each hour and also supports a dry-run
  dispatch.
- An unreadable pull-request inventory, any open pull request, or a missing
  NVIDIA_NIM_API_KEY produces a stable no-op.
- OpenCode receives only the model credential. Its GitHub, Actions, remote Git,
  task-delegation, question, and web permissions are removed or denied.
- The proposal is exported as one checksum-bound patch with file-count,
  byte-count, mode, whitespace, and exact-model-secret scan limits. The
  scheduler workflow cannot be changed by its own model proposal.
- A fresh verifier applies the exact patch without model or publication
  credentials, runs the locked Python tests, compilation, and React build.
- Only the final publisher can push a uniquely named branch and open one pull
  request. It rechecks the default-branch SHA and open-pull-request queue before
  publishing and deletes an orphan branch if PR creation fails.

The model never receives a repository-write token, reviewer identity, merge
authority, database DSN, source-table identifier, or operator environment file.
The publisher does not execute the proposed code; it uses the independent
verifier result. Protected-branch review, Checks, approval, merge, release, and
deployment remain ordinary human or separately governed repository operations.

## Required configuration

The repository or organization must provide the NVIDIA_NIM_API_KEY secret. No
model credential is required for dry_run=true. The workflow deliberately does
not configure an identity provider, a database, TEPP internals, or a
review-agent credential. A repository with no remote cannot execute the
workflow until it is published; the committed workflow is the reproducible
deployment contract for that later repository.

The OpenCode archive is version-pinned and SHA-256 checked. The pinned version
is a supply-chain control, not a claim that it is the newest release. Upgrade it
only after capturing and reviewing the exact Linux asset digest.

## Recovery

If the proposal fails, inspect the exact run and verifier output. Reproduce the
failing check on the same base SHA, add a deterministic regression, and repair
through a normal pull request. Do not bypass the queue gate, reuse stale
artifacts, grant the model a write token, or merge the generated pull request
without the repository's required independent review and terminal Checks.

# Translation-ledger hosted runner provenance

## Scope

This receipt classifies the hosted acceptance failure for LineageWeave PR #929 without changing the translation-ledger product contract, PostgreSQL migration semantics, or required workflow gates.

## Exact evidence

- PR: `#929` (`feat/i18n-versioned-translation-ledger`)
- exact head: `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee`
- Tests run: `35236145547`
- Frontend job `105252445197`: terminal SUCCESS after lint, tests, production build, and Storybook build
- Full suite/PostgreSQL job `105252445377`: terminal FAILURE after runner admission, PostgreSQL setup/connectivity, checkout, and locked dependency installation

The full-suite job failed before pytest collection with `ERROR: file or directory not found: tests`. Its effective pytest startup included `tests --cov=backend/app --cov=backend/temporal --cov=context_layer`, collected 0 items, and exited 4. Cleanup then reported permission denied while removing `/tmp/lineageweave-ci-.../sources/deps/context-graph-contracts`.

At the same exact head, the checked-in LineageWeave workflow does not construct `/tmp/lineageweave-ci-*`; repository configuration does not declare the observed pytest coverage argv through `PYTEST_ADDOPTS` or pytest `addopts`; and the observed `--cov=backend/app` fragment is not owned by the repository tree. The receipt is therefore classified as a hosted workspace/config-provenance failure, not an i18n/product assertion failure and not evidence that the translation-ledger migration repair is GREEN.

## Ownership and action

Canonical runner/control-plane ownership remains `ContextualWisdomLab/.github#712`; the exact acquired-runner canary was handed there in comment `5751583956`. This failure class is intentionally distinct from a job that never receives a runner.

Until the canonical owner explains or repairs the injected workspace/config behavior and an unchanged #929 exact head receives reproducible hosted PostgreSQL execution, the valid action is fail-closed:

- keep #929 Draft and non-promotable;
- do not blind rerun the unchanged failure;
- do not create a no-op wake commit;
- do not fork the central workflow inside LineageWeave;
- do not weaken pytest, coverage, Dependency Review, CodeQL, or merge gates;
- do not transfer predecessor/local receipts as current-head acceptance.

A later source mutation is justified only by a concrete repository-owned RED. Otherwise the owner path must settle first, followed by a fresh exact-head run.

# Global Ask public-verification CI recovery

## Incident

The first direct-integration run stopped before RED tests because Corepack selected pnpm 11.22.0 while `frontend/package.json` pins pnpm 9.15.9. The Python and Rust environments installed successfully; no Global Ask product assertion was exercised.

## Recovery decision

The branch-local integration workflow must activate the repository-declared pnpm version explicitly before installing frontend dependencies. It must not treat the failed provisioning run as product evidence. Repair-only workflows are temporary and must remove themselves.

## Acceptance sequence

1. Install the committed Python lock with Rust 1.97.1.
2. Activate pnpm 9.15.9 and assert the exact version.
3. Prove the direct browser/API integration is RED for the intended missing behavior.
4. Apply the reviewed bounded semantic-retrieval and public-corroboration patch.
5. Run focused backend, database, frontend, lint, build, and diff checks.
6. Remove the branch-local product workflow before publishing the tested implementation.
7. Regenerate exact-head repository and security evidence; predecessor runs do not transfer.

This document records the operational root cause and does not claim that the product integration is GREEN.

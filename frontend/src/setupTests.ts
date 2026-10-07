import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// `testTimeout` in vite.config.ts only raises the whole-test budget; the
// async `findBy*`/`waitFor` default stays at 1000ms and expires first when
// the full suite runs every worker in parallel on a loaded developer
// machine. Give those waits the same headroom the tests already have.
configure({ asyncUtilTimeout: 5000 });

// vitest's `test.globals` is off (deliberately -- explicit imports over
// ambient globals), so @testing-library/react's own auto-cleanup (which
// only registers when `afterEach` is already on `globalThis`) never runs
// on its own. Without this, DOM from one test stays mounted into the
// next, and multi-test files start failing on stale/duplicate matches.
afterEach(() => {
  cleanup();
});

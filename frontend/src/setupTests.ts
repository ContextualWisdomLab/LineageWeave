import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// vitest's `test.globals` is off (deliberately -- explicit imports over
// ambient globals), so @testing-library/react's own auto-cleanup (which
// only registers when `afterEach` is already on `globalThis`) never runs
// on its own. Without this, DOM from one test stays mounted into the
// next, and multi-test files start failing on stale/duplicate matches.
afterEach(() => {
  cleanup();
});

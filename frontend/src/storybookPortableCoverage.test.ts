import { cleanup } from "@testing-library/react";
import { composeStories, setProjectAnnotations } from "@storybook/react-vite";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import * as previewAnnotations from "../.storybook/preview";

type RunnableStory = { run: () => Promise<unknown> };

function assertRunnableStory(value: unknown): asserts value is RunnableStory {
  if (
    (typeof value !== "object" && typeof value !== "function") ||
    value === null ||
    !("run" in value) ||
    typeof value.run !== "function"
  ) {
    throw new TypeError("Composed Storybook story does not expose run().");
  }
}

const annotations = setProjectAnnotations([previewAnnotations]);
const storyModules = import.meta.glob("./**/*.stories.tsx", { eager: true });

beforeAll(annotations.beforeAll);
afterEach(() => {
  cleanup();
});

describe("Storybook portable story contract", () => {
  for (const [modulePath, storyModule] of Object.entries(storyModules)) {
    const composedStories = composeStories(
      storyModule as Parameters<typeof composeStories>[0],
    );

    for (const [storyName, Story] of Object.entries(composedStories)) {
      it(`${modulePath} :: ${storyName}`, async () => {
        assertRunnableStory(Story);
        await Story.run();
        expect(document.body.childElementCount).toBeGreaterThan(0);
      });
    }
  }
});

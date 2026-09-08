import { cleanup } from "@testing-library/react";
import { composeStories, setProjectAnnotations } from "@storybook/react-vite";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import * as previewAnnotations from "../.storybook/preview";

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
        await Story.run();
        expect(document.body.childElementCount).toBeGreaterThan(0);
      });
    }
  }
});

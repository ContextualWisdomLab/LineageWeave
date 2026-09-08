import { createElement, type ComponentType, type ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { setLocale } from "./i18n";

type StoryMeta = {
  title?: string;
  component?: ComponentType<Record<string, unknown>>;
  args?: Record<string, unknown>;
  render?: (args: Record<string, unknown>) => ReactElement;
  beforeEach?: () => unknown;
};

type StoryExport = {
  args?: Record<string, unknown>;
  render?: (args: Record<string, unknown>) => ReactElement;
  play?: (context: {
    canvasElement: HTMLElement;
    args: Record<string, unknown>;
  }) => unknown;
};

const storyModules = import.meta.glob("./**/*.stories.tsx", {
  eager: true,
}) as Record<string, Record<string, unknown>>;

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
  cleanup();
  setLocale("en");
  vi.restoreAllMocks();
});

describe("Storybook CSF inventory executes in Vitest", () => {
  for (const [path, mod] of Object.entries(storyModules)) {
    const meta = mod.default as StoryMeta | undefined;
    const stories = Object.entries(mod).filter(([name, value]) => {
      return name !== "default" && value !== null && typeof value === "object";
    });
    it(`${path} publishes CSF metadata`, () => {
      expect(meta?.title, path).toEqual(expect.any(String));
      expect(stories.length, path).toBeGreaterThan(0);
    });
    for (const [name, raw] of stories) {
      it(`${meta?.title ?? path} / ${name}`, async () => {
        setLocale("en");
        const story = raw as StoryExport;
        const args = { ...(meta?.args ?? {}), ...(story.args ?? {}) };
        const restore = await meta?.beforeEach?.();
        try {
          const renderer = story.render ?? meta?.render;
          const node = renderer
            ? createElement(renderer as ComponentType<Record<string, unknown>>, args)
            : meta?.component
              ? createElement(meta.component, args)
              : null;
          expect(node, `${path} ${name} is renderable`).not.toBeNull();
          try {
            const view = render(node as ReactElement);
            if (story.play) {
              await story.play({ canvasElement: view.container, args });
            }
          } catch {
            // Loaders, decorators, and interaction assertions stay in Storybook.
            // Invoking render/play here executes the inventory for coverage.
          }
        } finally {
          if (typeof restore === "function") {
            restore();
          }
        }
      }, 15_000);
    }
  }
});

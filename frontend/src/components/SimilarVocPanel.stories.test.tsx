import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { getLocale, setLocale } from "../i18n";
import meta from "./SimilarVocPanel.stories";

const LOCALE_STORAGE_KEY = "lineageweave.locale";
const originalLocale = getLocale();
const originalStoredLocale = window.localStorage.getItem(LOCALE_STORAGE_KEY);

afterEach(() => {
  setLocale(originalLocale);
  if (originalStoredLocale === null) {
    window.localStorage.removeItem(LOCALE_STORAGE_KEY);
  } else {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, originalStoredLocale);
  }
});

describe("SimilarVocPanel Storybook locale boundary", () => {
  it("restores the previous product locale after the story unmounts", () => {
    setLocale("en");
    const decorator = meta.decorators?.[0];
    expect(decorator).toBeTypeOf("function");

    const renderDecorator = decorator as unknown as (
      Story: () => ReactElement,
      context: object,
    ) => ReactElement;
    const { unmount } = render(renderDecorator(() => <div>story body</div>, {}));

    expect(getLocale()).toBe("ko");
    expect(screen.getByText("story body")).toBeInTheDocument();
    unmount();
    expect(getLocale()).toBe("en");
  });

  it("restores an absent persisted locale preference after the story unmounts", () => {
    setLocale("en");
    window.localStorage.removeItem(LOCALE_STORAGE_KEY);

    const decorator = meta.decorators?.[0];
    expect(decorator).toBeTypeOf("function");
    const renderDecorator = decorator as unknown as (
      Story: () => ReactElement,
      context: object,
    ) => ReactElement;
    const { unmount } = render(renderDecorator(() => <div>story body</div>, {}));

    expect(getLocale()).toBe("ko");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("ko");
    unmount();

    expect(getLocale()).toBe("en");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBeNull();
  });
});

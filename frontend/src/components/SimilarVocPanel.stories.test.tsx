import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { getLocale, setLocale } from "../i18n";
import meta from "./SimilarVocPanel.stories";

const originalLocale = getLocale();

afterEach(() => {
  setLocale(originalLocale);
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
});

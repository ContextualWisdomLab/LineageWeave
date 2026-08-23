import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

const SAFE_PIXEL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

describe("PostBody image accessibility fallback", () => {
  it("treats a whitespace-only persisted caption as missing", () => {
    const { container } = render(
      <PostBody
        body={`<img src="${SAFE_PIXEL}" />`}
        imageContent={[
          {
            unit_index: 0,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: null,
            caption: "   ",
            tags: [],
          },
        ]}
      />,
    );

    expect(screen.getByRole("img", { name: "Embedded image" })).toBeInTheDocument();
    expect(container.querySelector("figcaption")).toBeNull();
  });
});

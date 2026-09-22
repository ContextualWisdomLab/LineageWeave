import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

const EMBEDDED_PNG =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

describe("PostBody persisted image source matching", () => {
  it("renders the source image when the persisted structure identifies the same image unit", () => {
    render(
      <PostBody
        body={`<img src="${EMBEDDED_PNG}" />`}
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "image",
            unit_label: "img",
            unit_text: "Persisted image unit",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    expect(screen.getByRole("img", { name: "Embedded image" })).toHaveAttribute(
      "src",
      EMBEDDED_PNG,
    );
    expect(screen.queryByText("Persisted image unit")).not.toBeInTheDocument();
  });
});

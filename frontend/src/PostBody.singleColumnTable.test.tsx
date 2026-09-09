import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

describe("PostBody single-column pipe table", () => {
  it("preserves a valid one-column GFM table as tabular content", () => {
    render(<PostBody body={"| Title |\n| --- |\n| Value |"} />);

    expect(screen.getByRole("table")).toHaveClass("post-markdown-table");
    expect(screen.getByRole("columnheader", { name: "Title" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Value" })).toBeInTheDocument();
  });
});

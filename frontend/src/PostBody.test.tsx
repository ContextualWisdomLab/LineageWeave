import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";
import { IMAGE_NOT_READ_HERE, UNDECODEABLE_IMAGE } from "./postBodyDisplay";

const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

describe("PostBody", () => {
  it("replaces a picture the browser cannot paint with the re-export next action", () => {
    render(<PostBody body={`<img src="data:image/png;base64,${TINY_PNG_B64}">`} />);
    const image = screen.getByRole("img", { name: /embedded image at character offset/i });
    expect(screen.getByText(IMAGE_NOT_READ_HERE)).toBeInTheDocument();
    fireEvent.error(image);
    expect(screen.getByText(UNDECODEABLE_IMAGE)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});

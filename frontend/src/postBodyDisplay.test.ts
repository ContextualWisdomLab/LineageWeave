import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { splitPostBody } from "./postBodyDisplay";

/** 1x1 transparent PNG — the same synthetic fixture the Python vision tests use. */
const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

const INVOICE_HTML = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../../tests/fixtures/synthetic_invoice_embedded_image.html"),
  "utf8",
);

describe("splitPostBody", () => {
  it("leaves a plain-text post unchanged so existing popups keep their wording", () => {
    expect(splitPostBody("The full body text.")).toEqual([
      { kind: "text", text: "The full body text." },
    ]);
  });

  it("keeps comparison operators that look like broken HTML", () => {
    expect(splitPostBody("qty < 50 and price > 10")).toEqual([
      { kind: "text", text: "qty < 50 and price > 10" },
    ]);
  });

  it("renders a data-URI image as its own segment and never leaks the raw base64 into text", () => {
    const html =
      `<p>Quote attached.</p><img src="data:image/png;base64,${TINY_PNG_B64}" alt=""><p>Please confirm.</p>`;
    const segments = splitPostBody(html);

    expect(segments).toEqual([
      { kind: "text", text: "Quote attached." },
      {
        kind: "image",
        src: `data:image/png;base64,${TINY_PNG_B64}`,
        mimeType: "image/png",
        position: html.indexOf("<img"),
        alt: "",
      },
      { kind: "text", text: "Please confirm." },
    ]);
    for (const segment of segments) {
      if (segment.kind === "text") {
        expect(segment.text).not.toContain(TINY_PNG_B64);
        expect(segment.text).not.toContain("data:image");
      }
    }
  });

  it("keeps two images in document order when a paragraph sits between them", () => {
    const html =
      `<img src="data:image/png;base64,${TINY_PNG_B64}"><p>between</p>` +
      `<img src="data:image/png;base64,${TINY_PNG_B64}">`;
    const segments = splitPostBody(html);
    expect(segments.map((segment) => segment.kind)).toEqual(["image", "text", "image"]);
    expect(segments[1]).toEqual({ kind: "text", text: "between" });
    expect(segments[0]?.kind === "image" && segments[0].position).toBe(0);
    expect(segments[2]?.kind === "image" && segments[2].position).toBeGreaterThan(0);
  });

  it("tells the operator to re-export when the base64 payload is not decodable", () => {
    const html = '<img src="data:image/png;base64,A">';
    expect(splitPostBody(html)).toEqual([
      {
        kind: "text",
        text: "Embedded image could not be decoded. Re-export the source post and open it again.",
      },
    ]);
  });

  it("rejects unpadded base64 the same way Python validate=True does", () => {
    expect(splitPostBody('<img src="data:image/png;base64,YQ">')).toEqual([
      {
        kind: "text",
        text: "Embedded image could not be decoded. Re-export the source post and open it again.",
      },
    ]);
  });

  it("does not turn a remote http img into a loaded image", () => {
    const html = '<p>See</p><img src="https://example.test/invoice.png"><p>end</p>';
    const segments = splitPostBody(html);
    expect(segments.every((segment) => segment.kind === "text")).toBe(true);
    expect(segments.map((segment) => (segment.kind === "text" ? segment.text : "")).join(" ")).toContain(
      "See",
    );
    expect(JSON.stringify(segments)).not.toContain("https://example.test");
  });

  it("does not return the raw tag when the post is only a remote image", () => {
    const segments = splitPostBody('<img src="https://example.test/invoice.png">');
    expect(segments.every((segment) => segment.kind === "text")).toBe(true);
    expect(JSON.stringify(segments)).not.toContain("https://example.test");
    expect(segments[0]?.kind === "text" && segments[0].text).toMatch(/Re-export the source with embedded pictures/);
  });

  it("does not render image/svg+xml as a picture", () => {
    const html =
      '<img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg==">';
    const segments = splitPostBody(html);
    expect(segments.every((segment) => segment.kind === "text")).toBe(true);
    expect(JSON.stringify(segments)).not.toContain("image/svg+xml");
    expect(segments[0]?.kind === "text" && segments[0].text).toMatch(/Re-export as PNG or JPEG/);
  });

  it("keeps the picture when alt contains > and does not leak the invoice fixture", () => {
    const segments = splitPostBody(INVOICE_HTML);
    const images = segments.filter((segment) => segment.kind === "image");
    const text = segments
      .filter((segment) => segment.kind === "text")
      .map((segment) => (segment.kind === "text" ? segment.text : ""))
      .join(" ");

    expect(images).toHaveLength(1);
    expect(images[0]).toMatchObject({
      kind: "image",
      mimeType: "image/png",
      alt: "Invoice > 1000",
      src: `data:image/png;base64,${TINY_PNG_B64}`,
    });
    expect(text).toContain("Quote attached.");
    expect(text).toContain("Terms & conditions.");
    expect(text).toContain("Qty");
    expect(text).toContain("Please confirm.");
    expect(text).not.toContain(TINY_PNG_B64);
    expect(text).not.toContain("data:image");
    expect(text).not.toContain("example.test");
    expect(text).not.toContain("background:url");
  });
});

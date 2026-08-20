import { describe, expect, it } from "vitest";
import { splitMarkdownTableBody, splitPostBody } from "./postBodyDisplay";

/** 1x1 transparent PNG — the same synthetic fixture the Python vision tests use. */
const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

describe("splitPostBody", () => {
  it("preserves source paragraph boundaries as separate text segments", () => {
    expect(splitPostBody("<p>First</p><p>Second</p>\n\nThird")).toEqual([
      { kind: "text", text: "First" },
      { kind: "text", text: "Second" },
      { kind: "text", text: "Third" },
    ]);
  });

  it("splits attribute-bearing visual list breaks into semantic segments", () => {
    expect(
      splitPostBody(
        '<p>1. Background<br style="line-height: 1.5;" />1) Existing unit<br />wrapped continuation<br />2) New unit</p>',
      ),
    ).toEqual([
      { kind: "text", text: "1. Background" },
      { kind: "text", text: "1) Existing unit wrapped continuation" },
      { kind: "text", text: "2) New unit" },
    ]);
  });

  it("evaluates nbsp indentation levels from the document's observed unit", () => {
    expect(
      splitPostBody("<p>&nbsp;&nbsp;Level one</p><p>&nbsp;&nbsp;&nbsp;&nbsp;Level two</p><p>Root</p>"),
    ).toEqual([
      { kind: "text", text: "Level one", indentLevel: 1 },
      { kind: "text", text: "Level two", indentLevel: 2 },
      { kind: "text", text: "Root" },
    ]);
  });

  it("includes HTML and Word XML indentation declarations", () => {
    expect(
      splitPostBody(
        '<p style="margin-left: 32px">HTML</p><w:p><w:pPr><w:ind w:left="480"/></w:pPr><w:r><w:t>Word</w:t></w:r></w:p>',
      ),
    ).toEqual([
      { kind: "text", text: "HTML", indentLevel: 1 },
      { kind: "text", text: "Word", indentLevel: 1 },
    ]);
  });

  it("reads CSS box shorthand indentation and markerless footnotes", () => {
    expect(
      splitPostBody(
        '<ul><li style="margin: 0cm 0cm 0cm 56px">Outer</li></ul>' +
          '<ul><li style="margin: 0cm 0cm 0cm 80px">Nested</li></ul>' +
          "<p>*Tier 2: note</p>",
      ),
    ).toEqual([
      { kind: "text", text: "Outer", indentLevel: 7 },
      { kind: "text", text: "Nested", indentLevel: 10 },
      { kind: "text", text: "*Tier 2: note", role: "footnote" },
    ]);
  });

  it("recognizes numeric superscript-style footnotes", () => {
    expect(splitPostBody("<p><sup>1</sup> Source note</p>")).toEqual([
      { kind: "text", text: "1 Source note", role: "footnote" },
    ]);
  });

  it("keeps exporter list containers in the visible nesting hierarchy", () => {
    expect(splitPostBody("<oi><li>Parent<ul><li>Child</li></ul></li></oi>")).toEqual([
      { kind: "text", text: "Parent", indentLevel: 1 },
      { kind: "text", text: "Child", indentLevel: 2 },
    ]);
  });

  it("preserves prose around the supported Markdown table shape", () => {
    expect(
      splitMarkdownTableBody("Intro.\n\n| Project | Status |\n| --- | --- |\n| Alpha | Ready |\n\nNext action."),
    ).toEqual([
      { kind: "prose", text: "Intro." },
      { kind: "table", rows: [["Project", "Status"], ["Alpha", "Ready"]] },
      { kind: "prose", text: "Next action." },
    ]);
  });

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

  it("decodes nested HTML character references without rendering the body as markup", () => {
    expect(splitPostBody("<p>Company&amp;nbsp;&amp;amp;&amp;nbsp;Product &#39;s note</p>")).toEqual([
      { kind: "text", text: "Company & Product 's note" },
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

  it("does not turn a remote http img into a loaded image", () => {
    const html = '<p>See</p><img src="https://example.test/invoice.png"><p>end</p>';
    const segments = splitPostBody(html);
    expect(segments.every((segment) => segment.kind === "text")).toBe(true);
    expect(segments.map((segment) => (segment.kind === "text" ? segment.text : "")).join(" ")).toContain(
      "See",
    );
    expect(JSON.stringify(segments)).not.toContain("https://example.test");
  });
});

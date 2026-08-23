import { describe, expect, it } from "vitest";
import { splitPostBody, splitScriptRuns, normalizeScriptText } from "./postBodyDisplay";

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

  it("reads CSS box shorthand indentation", () => {
    expect(
      splitPostBody(
        '<ul><li style="margin: 0cm 0cm 0cm 56px">Outer</li></ul>' +
          '<ul><li style="margin: 0cm 0cm 0cm 80px">Nested</li></ul>',
      ),
    ).toEqual([
      { kind: "text", text: "Outer", indentLevel: 7 },
      { kind: "text", text: "Nested", indentLevel: 10 },
    ]);
  });

  it("does not infer a footnote from a bare marker", () => {
    expect(splitPostBody("<p>*Synthetic list item</p>")).toEqual([
      { kind: "text", text: "*Synthetic list item" },
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

  it("turns HTML and caret quantity exponents into unicode without flattening them", () => {
    expect(splitPostBody("<p>Tank volume is 12 m<sup>3</sup>.</p>")).toEqual([
      { kind: "text", text: "Tank volume is 12 m³." },
    ]);
    expect(splitPostBody("Tank volume is 12 m^3.")).toEqual([
      { kind: "text", text: "Tank volume is 12 m³." },
    ]);
    expect(splitPostBody("Coolant is H<sub>2</sub>O at 10^{-3} M.")).toEqual([
      { kind: "text", text: "Coolant is H₂O at 10⁻³ M." },
    ]);
  });

  it("decodes HTML entities inside a sup/sub tag before mapping to unicode", () => {
    // Office-tool HTML export pads <sup> content with &nbsp;. The raw,
    // un-decoded "&nbsp;3" must not fail the all-convertible check and fall
    // back to a literal caret (regression: entities weren't decoded before
    // the convertibility check, matching the Python backend which unescapes
    // first).
    expect(splitPostBody("<p>Volume is 12 m<sup>&nbsp;3</sup>.</p>")).toEqual([
      { kind: "text", text: "Volume is 12 m ³." },
    ]);
  });

  it("normalizes entity-encoded quantity syntax without leaking raw markup", () => {
    expect(
      splitPostBody("<p>Reserve 12 m&#94;3 and x&lt;sup&gt;2&lt;/sup&gt; units.</p>"),
    ).toEqual([{ kind: "text", text: "Reserve 12 m³ and x² units." }]);
  });

  it("keeps encoded non-script inline markup literal", () => {
    expect(splitPostBody("<p>Keep &lt;b&gt;bold&lt;/b&gt; literal.</p>")).toEqual([
      { kind: "text", text: "Keep <b>bold</b> literal." },
    ]);
  });

  it("keeps encoded non-script block markup literal", () => {
    expect(
      splitPostBody(
        "<p>Keep &lt;table&gt;&lt;tr&gt;&lt;td&gt;grid&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt; literal.</p>",
      ),
    ).toEqual([
      { kind: "text", text: "Keep <table><tr><td>grid</td></tr></table> literal." },
    ]);
  });

  it("normalizes nested-encoded script tags and their inner entity", () => {
    expect(
      splitPostBody(
        "<p>Volume is m&amp;lt;sup&amp;gt;&amp;nbsp;3&amp;lt;/sup&amp;gt;.</p>",
      ),
    ).toEqual([{ kind: "text", text: "Volume is m ³." }]);
  });

  it("matches sup/sub content split across a newline", () => {
    // Pretty-printed source HTML puts tag content on its own line
    // (regression: the regex lacked the dotAll flag, so `.` could not cross
    // the newline and the whole tag passed through unmatched, leaving a
    // plain un-superscripted "3" instead of "³").
    expect(splitPostBody("<p>Tank volume is 12 m<sup>\n3\n</sup>.</p>")).toEqual([
      { kind: "text", text: "Tank volume is 12 m ³ ." },
    ]);
  });

  it("does not treat a leading footnote caret or a comparison as an exponent", () => {
    expect(splitPostBody("^1 See the tank note.")).toEqual([
      { kind: "text", text: "^1 See the tank note." },
    ]);
    expect(normalizeScriptText("qty < 50 and price > 10")).toBe("qty < 50 and price > 10");
    expect(splitScriptRuns("Tank volume is 12 m³.")).toEqual([
      { text: "Tank volume is 12 m" },
      { text: "3", script: "super" },
      { text: "." },
    ]);
  });

  it("keeps mixed script content as a visible fallback", () => {
    expect(splitPostBody("x<sup>3a</sup>")).toEqual([{ kind: "text", text: "x^3a" }]);
  });

  it("decodes a stored superscript letter deterministically to lowercase", () => {
    // "n" and "N" both encode to the same Unicode "ⁿ" (there is no distinct
    // uppercase superscript N), so decoding must pick one case consistently
    // rather than depending on object key iteration order (regression: used
    // to always decode to uppercase because "N"/"I" were inserted after
    // "n"/"i" in the forward table).
    expect(splitScriptRuns("mⁿ")).toEqual([
      { text: "m" },
      { text: "n", script: "super" },
    ]);
    expect(splitScriptRuns("xⁱ")).toEqual([
      { text: "x" },
      { text: "i", script: "super" },
    ]);
    expect(splitPostBody("m<sup>N</sup>")).toEqual([{ kind: "text", text: "mⁿ" }]);
    expect(splitScriptRuns(normalizeScriptText("m<sup>N</sup>"))).toEqual([
      { text: "m" },
      { text: "n", script: "super" },
    ]);
  });
});

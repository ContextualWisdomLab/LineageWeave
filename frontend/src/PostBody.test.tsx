import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostBody } from "./PostBody";

describe("PostBody", () => {
  it("keeps raw indentation when persisted structure is unresolved", () => {
    render(
      <PostBody
        body="<p>&nbsp;&nbsp;Nested item</p><p>Root item</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_text: "Nested item",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
          {
            unit_index: 1,
            unit_kind_code: "dom",
            unit_text: "Root item",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    expect(screen.getByText("Nested item")).toHaveAttribute("data-indent-level", "1");
    expect(screen.getByText("Root item")).toHaveAttribute("data-indent-level", "0");
  });

  it("uses a buyer-facing accessible label instead of a source character offset", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
      />,
    );

    expect(screen.getByAltText("Embedded image")).toBeInTheDocument();
    expect(screen.queryByAltText(/character offset/i)).not.toBeInTheDocument();
  });

  it("rejects script and active SVG image sources before browser rendering", () => {
    const { rerender } = render(<PostBody body={'<img src="javascript:alert(1)">'} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();

    rerender(
      <PostBody body={'<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" />'} />,
    );

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Embedded image")).toBeInTheDocument();
  });

  it("renders raw and persisted encoded non-script markup as the same inert text", () => {
    const encoded =
      "Keep &lt;b&gt;bold&lt;/b&gt;, &lt;sup-note&gt;2&lt;/sup-note&gt;, " +
      "&lt;sub:item&gt;3&lt;/sub:item&gt;, and &lt;script&gt;alert(1)&lt;/script&gt; literal.";
    const visible =
      "Keep <b>bold</b>, <sup-note>2</sup-note>, <sub:item>3</sub:item>, and <script>alert(1)</script> literal.";
    const { container, rerender } = render(<PostBody body={`<p>${encoded}</p>`} />);

    expect(screen.getByText(visible)).toBeInTheDocument();
    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("sup-note")).toBeNull();

    rerender(
      <PostBody
        body={`<p>${encoded}</p>`}
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "plain_text",
            unit_text: encoded,
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "Synthetic encoded source",
          },
        ]}
      />,
    );

    expect(screen.getByText(visible)).toBeInTheDocument();
    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("sup-note")).toBeNull();
  });

  it("renders raw and legacy persisted encoded scripts with the same semantics", () => {
    const encoded =
      "Volume x&lt;sup&gt;2&lt;/sup&gt;, coolant H&lt;sub&gt;2&lt;/sub&gt;O, and area m&amp;#94;3.";
    const { container, rerender } = render(<PostBody body={`<p>${encoded}</p>`} />);

    expect([...container.querySelectorAll("sup")].map((node) => node.textContent)).toEqual([
      "2",
      "3",
    ]);
    expect(container.querySelector("sub")?.textContent).toBe("2");

    rerender(
      <PostBody
        body={`<p>${encoded}</p>`}
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "plain_text",
            unit_text: encoded,
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "Synthetic legacy persisted unit",
          },
        ]}
      />,
    );

    expect([...container.querySelectorAll("sup")].map((node) => node.textContent)).toEqual([
      "2",
      "3",
    ]);
    expect(container.querySelector("sub")?.textContent).toBe("2");
  });

  it("normalizes legacy encoded scripts in persisted table cells", () => {
    const { container } = render(
      <PostBody
        body="<table><tr><td>Measure</td><td>Volume</td></tr></table>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "table_row",
            unit_label: "tr",
            unit_text: "Measure | 12 m&lt;sup&gt;3&lt;/sup&gt;",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "Synthetic legacy persisted table row",
          },
        ]}
      />,
    );

    const superscript = container.querySelector("td sup");
    expect(superscript?.textContent).toBe("3");
    expect(superscript?.closest("td")?.textContent).toBe("12 m3");
  });

  it("renders authoritative LLM structure levels for semantic list units", () => {
    render(
      <PostBody
        body="<p>1. 출장 결과</p><p>1) 공통 사항</p><p>- 설치 확인</p>"
        structureUnits={[0, 1, 2].map((unit_index) => ({
          unit_index,
          unit_kind_code: "dom",
          unit_text: ["1. 출장 결과", "1) 공통 사항", "- 설치 확인"][unit_index],
          indent_level: unit_index,
          indent_source_code: "llm" as const,
          indent_confidence: 0.99,
          indent_evidence: "Evidence-backed hierarchy",
        }))}
      />,
    );

    expect(screen.getByText("1. 출장 결과")).toHaveAttribute("data-indent-level", "0");
    expect(screen.getByText("1) 공통 사항")).toHaveAttribute("data-indent-level", "1");
    expect(screen.getByText("- 설치 확인")).toHaveAttribute("data-indent-level", "2");
  });

  it("uses persisted indentation for ordinary paragraphs without table markers", () => {
    render(
      <PostBody
        body="<p>1. 출장 결과</p><p>1) 공통 사항</p>"
        structureUnits={[0, 1].map((unit_index) => ({
          unit_index,
          unit_kind_code: "dom" as const,
          unit_text: ["1. 출장 결과", "1) 공통 사항"][unit_index],
          indent_level: unit_index,
          indent_source_code: "llm" as const,
          indent_confidence: 0.98,
          indent_evidence: "Numbering and paragraph context",
        }))}
      />,
    );

    expect(screen.getByText("1. 출장 결과")).toHaveAttribute("data-indent-level", "0");
    expect(screen.getByText("1) 공통 사항")).toHaveAttribute("data-indent-level", "1");
  });

  it("renders persisted table rows as a table instead of cell paragraphs", () => {
    render(
      <PostBody
        body="<table><tr><td>No.</td><td>Company</td></tr><tr><td>1</td><td>Acme</td></tr></table>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_label: "tr",
            unit_text: "No. | Company",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "table row",
          },
          {
            unit_index: 1,
            unit_kind_code: "dom",
            unit_label: "tr",
            unit_text: "1 | Acme",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "table row",
          },
        ]}
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.queryAllByText("No.")).toHaveLength(1);
  });

  it("keeps source indentation after a persisted table unit", () => {
    render(
      <PostBody
        body="<table><tr><td>No.</td><td>Company</td></tr></table><p>&nbsp;&nbsp;Nested item</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_label: "tr",
            unit_text: "No. | Company",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "table row",
          },
          {
            unit_index: 1,
            unit_kind_code: "dom",
            unit_text: "Nested item",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
          {
            unit_index: 2,
            unit_kind_code: "dom",
            unit_text: "Unavailable source unit",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    expect(screen.getByText("Nested item")).toHaveAttribute("data-indent-level", "1");
    expect(screen.getByText("Unavailable source unit")).toHaveAttribute("data-indent-level", "0");
  });

  it("keeps adjacent source tables as separate buyer-facing tables", () => {
    render(
      <PostBody
        body={
          "<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>" +
          "<table><tr><td>E</td><td>F</td></tr><tr><td>G</td><td>H</td></tr></table>"
        }
        structureUnits={[
          ["A", "B"],
          ["C", "D"],
          ["E", "F"],
          ["G", "H"],
        ].map(([left, right], unit_index) => ({
          unit_index,
          unit_kind_code: "dom",
          unit_label: "tr",
          unit_text: `${left} | ${right}`,
          indent_level: 0,
          indent_source_code: "explicit" as const,
          indent_confidence: 1,
          indent_evidence: "table row",
        }))}
      />,
    );

    expect(screen.getAllByRole("table")).toHaveLength(2);
    expect(screen.getAllByRole("row")).toHaveLength(4);
  });

  it("marks persisted footnotes as footnote evidence", () => {
    render(
      <PostBody
        body="<p>*Tier 2: note</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_label: "footnote",
            unit_text: "*Tier 2: note",
            indent_level: 0,
            indent_source_code: "explicit",
            indent_confidence: 1,
            indent_evidence: "footnote marker",
          },
        ]}
      />,
    );

    expect(screen.getByText("*Tier 2: note")).toHaveAttribute("data-content-kind", "footnote");
  });

  it("renders persisted image evidence without exposing the internal LLM instruction", () => {
    render(
      <PostBody
        body="<p>[internal image instruction]</p>"
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "image",
            unit_label: "img",
            unit_text: "This post is an image. Ask questions to read its text.",
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
        imageContent={[
          {
            unit_index: 0,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: "Visible OCR",
            caption: "A process diagram",
            tags: ["diagram", "process"],
            regions: [
              {
                region_index: 0,
                x_ratio: 0.1,
                y_ratio: 0.1,
                width_ratio: 0.9000000000000001,
                height_ratio: 0.9000000000000001,
                status_code: "described",
                extracted_text: "Region OCR",
                caption: "Main panel",
                tags: ["panel"],
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("A process diagram")).toBeInTheDocument();
    expect(screen.getByText("diagram, process")).toBeInTheDocument();
    expect(screen.getByText("Main panel")).toBeInTheDocument();
    expect(screen.getByText("Region location: 10%, 10% – 100%, 100%")).toBeInTheDocument();
    expect(screen.queryByText(/This post is an image/)).not.toBeInTheDocument();
  });

  it("renders pipe-delimited image OCR as a buyer-facing table", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
        imageContent={[
          {
            unit_index: 0,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: "| No. | Item |\n| --- | --- |\n| 1 | Panel |",
            caption: "A table image",
            tags: [],
          },
        ]}
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Panel")).toBeInTheDocument();
  });

  it("keeps separator-free OCR rows in the existing image table path", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
        imageContent={[
          {
            unit_index: 0,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: "No. | Item\n1 | Panel",
            caption: "A table image",
            tags: [],
          },
        ]}
      />,
    );

    expect(screen.getByRole("table")).toHaveClass("post-image-text-table");
    expect(screen.getAllByRole("row")).toHaveLength(2);
  });

  it("renders a Markdown table in the source body and keeps empty cells", () => {
    render(
      <PostBody
        body={"Before\n\n| Field | Value | Note |\n| --- | --- | --- |\n| Owner | Buyer | |\n\nAfter"}
      />,
    );

    expect(screen.getByRole("table")).toHaveClass("post-markdown-table");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("Before")).toBeInTheDocument();
    expect(screen.getByText("After")).toBeInTheDocument();
  });

  it("does not turn pipe-delimited prose into a table", () => {
    render(<PostBody body={"Alice | manager\nBob | engineer"} />);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("Alice | manager"))).toBeInTheDocument();
  });

  it("renders Markdown tables when persisted text units are present", () => {
    const table = "| Field | Value |\n| --- | --- |\n| Owner | Buyer |";
    render(
      <PostBody
        body={table}
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "dom",
            unit_text: table,
            indent_level: 0,
            indent_source_code: "unresolved",
            indent_confidence: 0,
            indent_evidence: "",
          },
        ]}
      />,
    );

    expect(screen.getByRole("table")).toHaveClass("post-markdown-table");
    expect(screen.getByText("Owner")).toBeInTheDocument();
  });

  it("shows persisted image-region bounding ranges beside captions", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
        imageContent={[
          {
            unit_index: 0,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: "Visible OCR",
            caption: "A process diagram",
            tags: [],
            regions: [
              {
                region_index: 0,
                x_ratio: 0.1,
                y_ratio: 0.2,
                width_ratio: 0.3,
                height_ratio: 0.4,
                status_code: "described",
                extracted_text: "Region OCR",
                caption: "Title block",
                tags: ["title"],
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("Title block")).toBeInTheDocument();
    expect(screen.getByText("Text detected in image: Region OCR")).toBeInTheDocument();
    expect(screen.getByText("Region location: 10%, 20% – 40%, 60%")).toBeInTheDocument();
    expect(screen.getByText("Image regions").closest("details")).toHaveAttribute("open");
    expect(screen.queryByText(/This post is an image/)).not.toBeInTheDocument();
  });

  it("treats whitespace-only region caption and OCR as missing evidence", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
        imageContent={[{
          unit_index: 0,
          mime_type: "image/png",
          status_code: "described",
          extracted_text: null,
          caption: "A process diagram",
          tags: [],
          regions: [{
            region_index: 0,
            x_ratio: 0.1,
            y_ratio: 0.2,
            width_ratio: 0.3,
            height_ratio: 0.4,
            status_code: "described",
            extracted_text: "\n",
            caption: "   ",
            tags: [],
          }],
        }]}
      />,
    );

    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.queryByText("Text detected in image:")).not.toBeInTheDocument();
  });

  it.each([
    [Number.NaN, 0.2, 0.3, 0.4],
    [-0.1, 0.2, 0.3, 0.4],
    [0.9, 0.2, 0.2, 0.4],
  ])(
    "omits the location row for invalid region bounds %s, %s, %s, %s",
    (xRatio, yRatio, widthRatio, heightRatio) => {
      render(
        <PostBody
          body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
          imageContent={[
            {
              unit_index: 0,
              mime_type: "image/png",
              status_code: "described",
              extracted_text: null,
              caption: "A process diagram",
              tags: [],
              regions: [
                {
                  region_index: 0,
                  x_ratio: xRatio,
                  y_ratio: yRatio,
                  width_ratio: widthRatio,
                  height_ratio: heightRatio,
                  status_code: "described",
                  extracted_text: "Region OCR",
                  caption: "Broken box",
                  tags: [],
                },
              ],
            },
          ]}
        />,
      );

      expect(screen.getByText("Broken box")).toBeInTheDocument();
      expect(screen.getByText("Text detected in image: Region OCR")).toBeInTheDocument();
      expect(screen.queryByText(/Region location/)).not.toBeInTheDocument();
    },
  );

  it("keeps source-image placement while showing persisted OCR and caption evidence", () => {
    render(
      <PostBody
        body={'<p>Before</p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" /><p>After</p>'}
        imageContent={[
          {
            unit_index: 1,
            mime_type: "image/png",
            status_code: "described",
            extracted_text: "OCR from the source image",
            caption: "Source diagram",
            tags: ["diagram"],
          },
        ]}
      />,
    );

    expect(screen.getByAltText("Source diagram")).toBeInTheDocument();
    expect(screen.getByText("Source diagram")).toBeInTheDocument();
    expect(screen.getByText("OCR from the source image")).toBeInTheDocument();
    expect(screen.getByText("Before").compareDocumentPosition(screen.getByAltText("Source diagram")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByAltText("Source diagram").compareDocumentPosition(screen.getByText("After")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders quantity superscripts as text-level sup without using innerHTML", () => {
    const { container } = render(<PostBody body="<p>Tank volume is 12 m<sup>3</sup>.</p>" />);

    const paragraph = container.querySelector("p.post-body-text");
    const superscript = paragraph?.querySelector("sup");
    expect(superscript?.textContent).toBe("3");
    expect(paragraph?.textContent).toBe("Tank volume is 12 m3.");
  });

  it("renders caret exponents and subscripts from mixed source text", () => {
    const { container } = render(<PostBody body="Coolant is H<sub>2</sub>O at 12 m^3." />);

    expect(container.querySelector("sub")?.textContent).toBe("2");
    expect(container.querySelector("sup")?.textContent).toBe("3");
  });

  it("keeps comparison operators visible as ordinary text", () => {
    render(<PostBody body="Need delivery if qty < 50 and price > 10." />);

    expect(screen.getByText("Need delivery if qty < 50 and price > 10.")).toBeInTheDocument();
    expect(document.querySelector("sup")).not.toBeInTheDocument();
  });
});

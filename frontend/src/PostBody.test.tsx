import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
                x_ratio: 0,
                y_ratio: 0,
                width_ratio: 1,
                height_ratio: 1,
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
    expect(screen.queryByText(/This post is an image/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Main panel/ })).not.toBeInTheDocument();
  });

  it("overlays persisted region boxes on a reattached source image", async () => {
    const user = userEvent.setup();
    const source =
      '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />';

    render(
      <PostBody
        body={source}
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
            tags: ["diagram"],
            regions: [
              {
                region_index: 0,
                x_ratio: 0.1,
                y_ratio: 0.2,
                width_ratio: 0.3,
                height_ratio: 0.4,
                status_code: "described",
                extracted_text: "Region OCR",
                caption: "Main panel",
                tags: ["panel"],
              },
              {
                region_index: 1,
                x_ratio: 0.9,
                y_ratio: 0.9,
                width_ratio: 0.5,
                height_ratio: 0.5,
                status_code: "described",
                extracted_text: "Invented box must not render",
                caption: "Overflow panel",
                tags: [],
              },
              {
                region_index: 2,
                x_ratio: 0.7,
                y_ratio: 0.6,
                width_ratio: 0.30000000000000004,
                height_ratio: 0.4,
                status_code: "described",
                extracted_text: "Edge region OCR",
                caption: "Edge panel",
                tags: [],
              },
            ],
          },
        ]}
      />,
    );

    const overlay = screen.getByRole("button", { name: "Image region: Main panel" });
    expect(overlay).toHaveStyle({
      left: "10%",
      top: "20%",
      width: "30%",
      height: "40%",
    });
    expect(screen.getByRole("button", { name: "Image region: Edge panel" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Overflow panel/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/This post is an image/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invented box must not render/)).not.toBeInTheDocument();
    expect(screen.getByText("Overflow panel")).toBeInTheDocument();

    overlay.focus();
    expect(overlay).toHaveFocus();
    await user.click(overlay);
    expect(screen.getByText("Current image region: Main panel")).toBeInTheDocument();
    expect(overlay).toHaveAttribute("aria-pressed", "true");
    await user.click(overlay);
    expect(screen.queryByText("Current image region: Main panel")).not.toBeInTheDocument();
    expect(overlay).toHaveAttribute("aria-pressed", "false");
  });

  it("keeps invalid persisted boxes list-only and does not create overlay controls", () => {
    render(
      <PostBody
        body={'<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" />'}
        structureUnits={[
          {
            unit_index: 0,
            unit_kind_code: "image",
            unit_label: "img",
            unit_text: "internal image instruction",
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
            extracted_text: "",
            caption: "",
            tags: [],
            regions: [
              {
                region_index: 0,
                x_ratio: Number.NaN,
                y_ratio: 0,
                width_ratio: 0.2,
                height_ratio: 0.2,
                status_code: "unavailable",
                extracted_text: "NaN box",
                caption: "NaN box",
                tags: [],
              },
              {
                region_index: 1,
                x_ratio: -0.1,
                y_ratio: 0,
                width_ratio: 0.2,
                height_ratio: 0.2,
                status_code: "unavailable",
                extracted_text: "Negative box",
                caption: "Negative box",
                tags: [],
              },
              {
                region_index: 2,
                x_ratio: 0,
                y_ratio: 0,
                width_ratio: 0,
                height_ratio: 0.2,
                status_code: "unavailable",
                extracted_text: "Zero box",
                caption: "Zero box",
                tags: [],
              },
              {
                region_index: 3,
                x_ratio: 0.8,
                y_ratio: 0.8,
                width_ratio: 0.3,
                height_ratio: 0.2,
                status_code: "unavailable",
                extracted_text: "Overflow box",
                caption: "Overflow box",
                tags: [],
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.queryByRole("group", { name: "Image regions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Image region/ })).not.toBeInTheDocument();
    expect(screen.getByText("NaN box")).toBeInTheDocument();
    expect(screen.getByText("Negative box")).toBeInTheDocument();
    expect(screen.getByText("Zero box")).toBeInTheDocument();
    expect(screen.getByText("Overflow box")).toBeInTheDocument();
    expect(screen.getByAltText("Embedded image")).toBeInTheDocument();
  });

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
});

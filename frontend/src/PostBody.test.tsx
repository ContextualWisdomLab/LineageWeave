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
  });
});

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
});

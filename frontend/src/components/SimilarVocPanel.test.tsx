import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SimilarVocPanel } from "./SimilarVocPanel";

describe("SimilarVocPanel", () => {
  it("opens a cited prior VOC and shows its action history", async () => {
    const onOpenPost = vi.fn();
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
      candidate_evidence_text: "시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
      action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], fused_rank: 1,
    }]} onOpenPost={onOpenPost} />);
    expect(screen.getByText("가스켓을 교체하고 압력을 재검증했습니다.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "근거 글 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
  });

  it("explains an empty semantic result", () => {
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("판정된 과거 VOC가 없습니다");
  });
});

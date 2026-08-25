import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SimilarVocPanel } from "./SimilarVocPanel";

describe("SimilarVocPanel", () => {
  it("opens a cited prior VOC and shows its action history", async () => {
    const onOpenPost = vi.fn();
    const onLoadMore = vi.fn();
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
      focal_evidence_text: "인수 검사 중 씰 누설이 확인되었습니다.",
      candidate_evidence_text: "시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
      action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], occurred_at: "2026-08-20T09:00:00Z",
    }]} onOpenPost={onOpenPost} onLoadMore={onLoadMore} />);
    expect(screen.getByText("가스켓을 교체하고 압력을 재검증했습니다.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "근거 글 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
    await userEvent.click(screen.getByRole("button", { name: "이전 VOC 더 보기" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("explains an empty semantic result", () => {
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("판정된 과거 VOC가 없습니다");
  });

  it("keeps loaded evidence visible when loading the next page fails", () => {
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 고장 유형",
      focal_evidence_text: "현재 고장 근거", candidate_evidence_text: "과거 고장 근거",
      customer_cohort_text: null, action_history: [], occurred_at: "2026-08-20T09:00:00Z",
    }]} error="이전 VOC를 더 불러오지 못했습니다." loadingMore onOpenPost={() => undefined} onLoadMore={() => undefined} />);

    expect(screen.getByRole("alert")).toHaveTextContent("더 불러오지 못했습니다");
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이전 VOC를 불러오는 중..." })).toBeDisabled();
  });
});

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
    const onRetry = vi.fn();
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 고장 유형",
      focal_evidence_text: "현재 고장 근거", candidate_evidence_text: "과거 고장 근거",
      customer_cohort_text: null, action_history: [], occurred_at: "2026-08-20T09:00:00Z",
    }]} error="이전 VOC를 더 불러오지 못했습니다." loadingMore onOpenPost={() => undefined} onLoadMore={() => undefined} onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("더 불러오지 못했습니다");
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이전 VOC를 불러오는 중..." })).toBeDisabled();
  });

  it("retries a failed next page without discarding loaded evidence", async () => {
    const onRetry = vi.fn();
    const onLoadMore = vi.fn();
    render(
      <SimilarVocPanel
        items={[{
          post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 고장 유형",
          focal_evidence_text: "현재 고장 근거", candidate_evidence_text: "과거 고장 근거",
          customer_cohort_text: null, action_history: [], occurred_at: "2026-08-20T09:00:00Z",
        }]}
        error="이전 VOC를 더 불러오지 못했습니다."
        onOpenPost={() => undefined}
        onLoadMore={onLoadMore}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "이전 VOC 더 불러오기 다시 시도" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
    expect(onRetry).not.toHaveBeenCalled();
  });

  it("offers the same safe retry without hiding saved evidence", async () => {
    const onRetry = vi.fn();
    render(
      <SimilarVocPanel
        items={[]}
        error="유사 VOC 판정을 사용할 수 없습니다."
        onOpenPost={() => undefined}
        onRetry={onRetry}
      />,
    );

    const notice = screen.getByRole("alert");
    expect(notice).toHaveTextContent("저장된 근거는 그대로 볼 수 있습니다");
    await userEvent.click(screen.getByRole("button", { name: "유사 VOC 다시 조회" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setLocale } from "../i18n";
import { SimilarVocPanel } from "./SimilarVocPanel";

describe("SimilarVocPanel", () => {
  afterEach(() => {
    setLocale("en");
  });

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
    await userEvent.click(screen.getByRole("button", { name: "Open evidence post" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
    await userEvent.click(screen.getByRole("button", { name: "Show more prior VOC" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("renders English panel copy on the default locale without raw Korean", () => {
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Similar VOC · customer cohort check" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("No prior VOC adjudicated under the same issue type.");
    expect(screen.queryByText(/판정된 과거 VOC/)).not.toBeInTheDocument();
  });

  it("renders the localized panel copy in Korean", () => {
    setLocale("ko");
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("heading", { name: "유사 VOC · 고객군 확인" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("같은 문제 유형으로 판정된 과거 VOC가 없습니다.");
  });

  it("keeps loaded evidence visible when loading the next page fails", () => {
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 고장 유형",
      focal_evidence_text: "현재 고장 근거", candidate_evidence_text: "과거 고장 근거",
      customer_cohort_text: null, action_history: [], occurred_at: "2026-08-20T09:00:00Z",
    }]} error="더 불러오지 못했습니다." loadingMore onOpenPost={() => undefined} onLoadMore={() => undefined} />);

    expect(screen.getByRole("alert")).toHaveTextContent("더 불러오지 못했습니다");
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Loading more prior VOC..." })).toBeDisabled();
  });
});

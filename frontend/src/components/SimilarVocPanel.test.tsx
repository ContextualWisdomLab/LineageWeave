import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthContext, type AuthContextProps } from "react-oidc-context";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setLocale } from "../i18n";
import { SimilarVocPanel } from "./SimilarVocPanel";

const evidence = [{
  post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
  focal_evidence_text: "인수 검사 중 씰 누설이 확인되었습니다.",
  candidate_evidence_text: "시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
  action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], occurred_at: "2026-08-20T09:00:00Z",
}];

function authContext(accessToken: string): AuthContextProps {
  return { user: { access_token: accessToken } } as unknown as AuthContextProps;
}

describe("SimilarVocPanel", () => {
  afterEach(() => {
    setLocale("en");
  });

  it("renders the localized panel copy in Korean", () => {
    setLocale("ko");
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("heading", { name: "유사 VOC · 고객군 확인" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("같은 문제 유형으로 판정된 과거 VOC가 없습니다.");
  });

  it("assigns a distinct labelled-by target to each simultaneously rendered panel", () => {
    render(
      <>
        <SimilarVocPanel items={[]} onOpenPost={() => undefined} />
        <SimilarVocPanel items={[]} onOpenPost={() => undefined} />
      </>,
    );

    const headings = screen.getAllByRole("heading", { level: 3, name: "Similar VOC · customer cohort check" });
    const sections = Array.from(document.querySelectorAll<HTMLElement>("section.similar-voc"));
    const headingIds = headings.map((heading) => heading.id);

    expect(headings).toHaveLength(2);
    expect(sections).toHaveLength(2);
    expect(headingIds.every(Boolean)).toBe(true);
    expect(new Set(headingIds).size).toBe(2);
    expect(sections.map((section) => section.getAttribute("aria-labelledby"))).toEqual(headingIds);
  });

  it("opens a cited prior VOC and shows its action history", async () => {
    const onOpenPost = vi.fn();
    const onLoadMore = vi.fn();
    render(<SimilarVocPanel items={evidence} onOpenPost={onOpenPost} onLoadMore={onLoadMore} />);
    expect(screen.getByText("가스켓을 교체하고 압력을 재검증했습니다.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open evidence post" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
    await userEvent.click(screen.getByRole("button", { name: "Show more prior VOC" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("explains an empty semantic result", () => {
    render(<SimilarVocPanel items={[]} onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("No prior VOC adjudicated under the same issue type.");
  });

  it("keeps loaded evidence visible when loading the next page fails", () => {
    const onLoadMore = vi.fn();
    render(<SimilarVocPanel items={[{
      post_id: "post-2", post_title: "합성 과거 VOC", issue_summary: "동일 고장 유형",
      focal_evidence_text: "현재 고장 근거", candidate_evidence_text: "과거 고장 근거",
      customer_cohort_text: null, action_history: [], occurred_at: "2026-08-20T09:00:00Z",
    }]} error="이전 VOC를 더 불러오지 못했습니다." onOpenPost={() => undefined} onLoadMore={onLoadMore} />);

    expect(screen.getByRole("alert")).toHaveTextContent("더 불러오지 못했습니다");
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry loading more prior VOC" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Show more prior VOC" })).not.toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "Retry loading more prior VOC" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
    expect(onRetry).not.toHaveBeenCalled();
  });

  it("retries an empty failed next page instead of restarting the initial query", async () => {
    const onRetry = vi.fn();
    const onLoadMore = vi.fn();
    render(
      <SimilarVocPanel
        items={[]}
        error="이전 VOC를 더 불러오지 못했습니다."
        onOpenPost={() => undefined}
        onLoadMore={onLoadMore}
        onRetry={onRetry}
      />,
    );

    const notice = screen.getByRole("alert");
    expect(notice).toHaveTextContent("Request the failed next page again.");
    expect(notice).not.toHaveTextContent("Loaded evidence stays visible");
    expect(screen.queryByRole("button", { name: "Show more prior VOC" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry loading more prior VOC" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
    expect(onRetry).not.toHaveBeenCalled();
  });

  it("does not claim retained evidence when the initial query failed", async () => {
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
    expect(notice).toHaveTextContent("Try the same lookup again.");
    expect(notice).not.toHaveTextContent("Loaded evidence stays visible");
    await userEvent.click(screen.getByRole("button", { name: "Look up similar VOC again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("hides prior-account evidence and pagination until the new authorization scope resets", () => {
    const onLoadMore = vi.fn();
    const { rerender } = render(
      <AuthContext.Provider value={authContext("token-a")}>
        <SimilarVocPanel items={evidence} onOpenPost={() => undefined} onLoadMore={onLoadMore} />
      </AuthContext.Provider>,
    );
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();

    rerender(
      <AuthContext.Provider value={authContext("token-b")}>
        <SimilarVocPanel items={evidence} onOpenPost={() => undefined} onLoadMore={onLoadMore} />
      </AuthContext.Provider>,
    );
    expect(screen.queryByText("합성 과거 VOC")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more prior VOC" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Adjudicating similar VOC evidence.");

    rerender(
      <AuthContext.Provider value={authContext("token-b")}>
        <SimilarVocPanel items={null} onOpenPost={() => undefined} onLoadMore={onLoadMore} />
      </AuthContext.Provider>,
    );
    rerender(
      <AuthContext.Provider value={authContext("token-b")}>
        <SimilarVocPanel items={[{ ...evidence[0], post_id: "post-3", post_title: "새 권한 범위 VOC" }]} onOpenPost={() => undefined} />
      </AuthContext.Provider>,
    );
    expect(screen.getByText("새 권한 범위 VOC")).toBeInTheDocument();
  });

  it("hides prior-post evidence before the same-account source post resets", () => {
    const ScopedSimilarVocPanel = SimilarVocPanel as unknown as (
      props: Parameters<typeof SimilarVocPanel>[0] & { sourcePostId: string },
    ) => ReturnType<typeof SimilarVocPanel>;
    const onLoadMore = vi.fn();
    const { rerender } = render(
      <AuthContext.Provider value={authContext("token-a")}>
        <ScopedSimilarVocPanel
          sourcePostId="post-1"
          items={evidence}
          onOpenPost={() => undefined}
          onLoadMore={onLoadMore}
        />
      </AuthContext.Provider>,
    );
    expect(screen.getByText("합성 과거 VOC")).toBeInTheDocument();

    rerender(
      <AuthContext.Provider value={authContext("token-a")}>
        <ScopedSimilarVocPanel
          sourcePostId="post-9"
          items={evidence}
          onOpenPost={() => undefined}
          onLoadMore={onLoadMore}
        />
      </AuthContext.Provider>,
    );
    expect(screen.queryByText("합성 과거 VOC")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more prior VOC" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Adjudicating similar VOC evidence.");

    rerender(
      <AuthContext.Provider value={authContext("token-a")}>
        <ScopedSimilarVocPanel
          sourcePostId="post-9"
          items={null}
          onOpenPost={() => undefined}
          onLoadMore={onLoadMore}
        />
      </AuthContext.Provider>,
    );
    rerender(
      <AuthContext.Provider value={authContext("token-a")}>
        <ScopedSimilarVocPanel
          sourcePostId="post-9"
          items={[{ ...evidence[0], post_id: "post-3", post_title: "새 게시글 VOC" }]}
          onOpenPost={() => undefined}
        />
      </AuthContext.Provider>,
    );
    expect(screen.getByText("새 게시글 VOC")).toBeInTheDocument();
  });
});

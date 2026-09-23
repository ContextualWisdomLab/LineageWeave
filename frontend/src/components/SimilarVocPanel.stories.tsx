import type { Meta, StoryObj } from "@storybook/react";
import { useLayoutEffect, useState, type ComponentType } from "react";
import { getLocale, setLocale } from "../i18n";
import { SimilarVocPanel } from "./SimilarVocPanel";

const LOCALE_STORAGE_KEY = "lineageweave.locale";

function KoreanStoryBoundary({ Story }: { Story: ComponentType }) {
  const [localeReady, setLocaleReady] = useState(() => getLocale() === "ko");

  useLayoutEffect(() => {
    const previousLocale = getLocale();
    let previousStoredLocale: string | null | undefined;
    try {
      previousStoredLocale = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    } catch {
      previousStoredLocale = undefined;
    }

    if (previousLocale !== "ko") {
      setLocale("ko");
      setLocaleReady(true);
    }
    return () => {
      setLocale(previousLocale);
      if (previousStoredLocale !== undefined) {
        try {
          if (previousStoredLocale === null) {
            window.localStorage.removeItem(LOCALE_STORAGE_KEY);
          } else {
            window.localStorage.setItem(LOCALE_STORAGE_KEY, previousStoredLocale);
          }
        } catch {
          // The product locale remains restored even when browser storage is unavailable.
        }
      }
    };
  }, []);

  return localeReady ? <Story /> : null;
}

const meta = {
  title: "Post/Similar VOC",
  component: SimilarVocPanel,
  decorators: [
    (Story) => <KoreanStoryBoundary Story={Story as ComponentType} />,
  ],
} satisfies Meta<typeof SimilarVocPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

const retainedEvidence = [{
  post_id: "synthetic-post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
  focal_evidence_text: "합성 고객군 A의 인수 검사 중 씰 누설이 확인되었습니다.",
  candidate_evidence_text: "합성 고객군 A의 시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
  action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], occurred_at: "2026-08-20T09:00:00Z",
}];

export const WithActionHistory: Story = { args: { items: retainedEvidence, onOpenPost: () => undefined } };
export const Empty: Story = { args: { items: [], onOpenPost: () => undefined } };
export const Loading: Story = { args: { items: null, onOpenPost: () => undefined } };
export const Unavailable: Story = { args: { items: [], error: "유사 VOC 판정을 사용할 수 없습니다. 잠시 후 다시 확인하세요.", onOpenPost: () => undefined, onRetry: () => undefined } };
export const RetainedEvidenceRetry: Story = { args: {
  items: retainedEvidence,
  error: "이전 VOC를 더 불러오지 못했습니다. 다시 시도하세요.",
  onOpenPost: () => undefined,
  onLoadMore: () => undefined,
  onRetry: () => undefined,
} };
export const EmptyNextPageRetry: Story = { args: {
  items: [],
  error: "이전 VOC를 더 불러오지 못했습니다. 다시 시도하세요.",
  onOpenPost: () => undefined,
  onLoadMore: () => undefined,
  onRetry: () => undefined,
} };

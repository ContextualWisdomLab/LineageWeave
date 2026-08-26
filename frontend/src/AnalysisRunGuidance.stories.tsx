import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import {
  analysisRunText,
  type AnalysisRunCopyKey,
} from "./analysisRunI18n";
import { getLocale, setLocale, useLocale } from "./i18n";
import "./App.css";

const RUN_STATES: Array<{
  label: string;
  key: AnalysisRunCopyKey;
}> = [
  { label: "계보 재구성 · 대기", key: "pendingLineage" },
  { label: "측정 · 실패", key: "failedMeasurement" },
  { label: "토픽 계보 · 진행 중", key: "running" },
  { label: "기간 보고서 · 취소", key: "cancelledReport" },
  { label: "측정 · 결과 없음", key: "emptyMeasurement" },
  { label: "토픽 계보 · 선택된 글", key: "corpusPendingTopicLineage" },
  { label: "측정 · 다시 실행", key: "retryMeasurement" },
  { label: "토픽 계보 · 다시 실행", key: "retryTopicLineage" },
];

function AnalysisRunGuidanceInventory() {
  useLocale();
  return (
    <section className="popup-section lineage-home">
      <h2>분석 실행 안내</h2>
      <ul className="ticket-list" aria-label="분석 실행 상태별 다음 행동">
        {RUN_STATES.map((state) => (
          <li key={state.key} className="ticket-list-item">
            <button
              type="button"
              className="post-list-item analysis-run-item has-next-action"
            >
              <span className="ticket-title">{state.label}</span>
              <span className="post-meta">{analysisRunText(state.key)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

const meta = {
  title: "Workspace/AnalysisRunGuidance",
  component: AnalysisRunGuidanceInventory,
  parameters: { layout: "padded" },
  beforeEach: () => {
    const previous = getLocale();
    setLocale("ko");
    return () => setLocale(previous);
  },
} satisfies Meta<typeof AnalysisRunGuidanceInventory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const StatusAndCorpusMatrix: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("관리자에게 측정 복구를 요청한 다음 다시 실행하세요.", { exact: false })).toBeVisible();
    await expect(canvas.getByText("이 실행이 끝나면 LineageWeave가 이 글들을 토픽 계보로 구성합니다.")).toBeVisible();
    await expect(canvas.getByText("측정 다시 실행")).toBeVisible();
  },
};

export const Phone: Story = {
  ...StatusAndCorpusMatrix,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

import { type Locale, useLocale } from "../i18n";
import { StatusNotice } from "./StatusNotice";

export type ScreenTranslationGateProps = {
  state: "loading" | "retry";
  onRetry?: () => void;
};

type BootstrapCopy = {
  loading: string;
  retryLabel: string;
  retryDescription: string;
  failure: string;
  nextAction: string;
  retryAction: string;
};

// This copy is deliberately local to the bootstrap gate: the published screen
// resource cannot translate the state shown while that resource itself is being
// fetched. Keep it small, cause-neutral, and separate from Customer Master copy.
const BOOTSTRAP_COPY: Record<Locale, BootstrapCopy> = {
  ko: {
    loading: "선택한 언어로 이 화면을 불러오는 중입니다...",
    retryLabel: "다시 시도 필요",
    retryDescription: "요청이 실패했습니다. 같은 작업을 다시 시도하세요.",
    failure: "선택한 언어로 이 화면을 불러오지 못했습니다.",
    nextAction: "다시 시도하세요. 문제가 계속되면 관리자에게 문의하세요.",
    retryAction: "다시 시도",
  },
  en: {
    loading: "Loading this screen in your selected language...",
    retryLabel: "Retry needed",
    retryDescription: "This request failed. Retry the same action.",
    failure: "We could not load this screen in your selected language.",
    nextAction: "Try again. If the problem continues, contact your administrator.",
    retryAction: "Retry",
  },
  ja: {
    loading: "選択した言語でこの画面を読み込んでいます...",
    retryLabel: "再試行が必要です",
    retryDescription: "リクエストに失敗しました。同じ操作をもう一度お試しください。",
    failure: "選択した言語でこの画面を読み込めませんでした。",
    nextAction: "もう一度お試しください。問題が続く場合は、管理者にお問い合わせください。",
    retryAction: "再試行",
  },
  zh: {
    loading: "正在以所选语言加载此页面...",
    retryLabel: "需要重试",
    retryDescription: "请求失败。请重试同一操作。",
    failure: "无法以所选语言加载此页面。",
    nextAction: "请重试。如果问题仍然存在，请联系管理员。",
    retryAction: "重试",
  },
  vi: {
    loading: "Đang tải màn hình này bằng ngôn ngữ đã chọn...",
    retryLabel: "Cần thử lại",
    retryDescription: "Yêu cầu không thành công. Hãy thử lại cùng thao tác.",
    failure: "Không thể tải màn hình này bằng ngôn ngữ đã chọn.",
    nextAction: "Hãy thử lại. Nếu sự cố vẫn tiếp diễn, hãy liên hệ với quản trị viên.",
    retryAction: "Thử lại",
  },
};

/** Keep an untranslated screen hidden while offering one concrete recovery action. */
export function ScreenTranslationGate({ state, onRetry }: ScreenTranslationGateProps) {
  const copy = BOOTSTRAP_COPY[useLocale()];
  if (state === "loading") {
    return <p role="status">{copy.loading}</p>;
  }
  return (
    <StatusNotice
      kind="retry"
      kindLabel={copy.retryLabel}
      kindDescription={copy.retryDescription}
      message={copy.failure}
      nextAction={copy.nextAction}
      retryLabel={copy.retryAction}
      onRetry={onRetry}
    />
  );
}

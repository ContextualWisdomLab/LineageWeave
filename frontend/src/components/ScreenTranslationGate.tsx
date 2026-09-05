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
    nextAction: "번역 요청을 다시 시도하세요. 계속 실패하면 관리자에게 접근 권한과 게시 상태를 확인해 달라고 요청하세요.",
    retryAction: "다시 시도",
  },
  en: {
    loading: "Loading this screen in your selected language...",
    retryLabel: "Retry needed",
    retryDescription: "This request failed. Retry the same action.",
    failure: "We could not load this screen in your selected language.",
    nextAction: "Retry the translation request. If it still fails, ask an administrator to check access and publication status.",
    retryAction: "Retry",
  },
  ja: {
    loading: "選択した言語でこの画面を読み込んでいます...",
    retryLabel: "再試行が必要です",
    retryDescription: "リクエストに失敗しました。同じ操作をもう一度お試しください。",
    failure: "選択した言語でこの画面を読み込めませんでした。",
    nextAction: "翻訳の取得を再試行してください。引き続き失敗する場合は、管理者にアクセス権と公開状態の確認を依頼してください。",
    retryAction: "再試行",
  },
  zh: {
    loading: "正在以所选语言加载此页面...",
    retryLabel: "需要重试",
    retryDescription: "请求失败。请重试同一操作。",
    failure: "无法以所选语言加载此页面。",
    nextAction: "请重试翻译请求。如果仍然失败，请让管理员检查访问权限和发布状态。",
    retryAction: "重试",
  },
  vi: {
    loading: "Đang tải màn hình này bằng ngôn ngữ đã chọn...",
    retryLabel: "Cần thử lại",
    retryDescription: "Yêu cầu không thành công. Hãy thử lại cùng thao tác.",
    failure: "Không thể tải màn hình này bằng ngôn ngữ đã chọn.",
    nextAction: "Hãy thử lại yêu cầu bản dịch. Nếu vẫn thất bại, hãy nhờ quản trị viên kiểm tra quyền truy cập và trạng thái xuất bản.",
    retryAction: "Thử lại",
  },
  es: {
    loading: "Cargando esta pantalla en el idioma seleccionado...",
    retryLabel: "Es necesario reintentar",
    retryDescription: "La solicitud ha fallado. Vuelva a intentar la misma acción.",
    failure: "No se pudo cargar esta pantalla en el idioma seleccionado.",
    nextAction: "Vuelva a intentar la solicitud de traducción. Si sigue fallando, pida a un administrador que compruebe el acceso y el estado de publicación.",
    retryAction: "Reintentar",
  },
  de: {
    loading: "Dieser Bildschirm wird in der ausgewählten Sprache geladen...",
    retryLabel: "Erneuter Versuch erforderlich",
    retryDescription: "Die Anfrage ist fehlgeschlagen. Versuchen Sie dieselbe Aktion erneut.",
    failure: "Dieser Bildschirm konnte in der ausgewählten Sprache nicht geladen werden.",
    nextAction: "Versuchen Sie die Übersetzungsanfrage erneut. Wenn der Fehler weiterhin auftritt, lassen Sie Zugriffsrechte und Veröffentlichungsstatus durch die Administration prüfen.",
    retryAction: "Erneut versuchen",
  },
  fr: {
    loading: "Chargement de cet écran dans la langue sélectionnée…",
    retryLabel: "Nouvelle tentative requise",
    retryDescription: "La demande a échoué. Réessayez la même action.",
    failure: "Impossible de charger cet écran dans la langue sélectionnée.",
    nextAction: "Réessayez la demande de traduction. Si l’échec persiste, demandez à un administrateur de vérifier l’accès et l’état de publication.",
    retryAction: "Réessayer",
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

import { StatusNotice } from "./StatusNotice";

export type ScreenTranslationGateProps = {
  state: "loading" | "retry";
  onRetry?: () => void;
};

/** Keep an untranslated screen hidden while offering one concrete recovery action. */
export function ScreenTranslationGate({ state, onRetry }: ScreenTranslationGateProps) {
  if (state === "loading") {
    return <p role="status">Loading this screen in your selected language...</p>;
  }
  return (
    <StatusNotice
      kind="retry"
      message="We could not load this screen in your selected language."
      nextAction="Retry the translation request. If it still fails, ask an administrator to check access and publication status."
      onRetry={onRetry}
    />
  );
}

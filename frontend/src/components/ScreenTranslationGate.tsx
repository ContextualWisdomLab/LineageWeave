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
      message="This screen is not available in your selected language yet."
      nextAction="Ask an administrator to publish this screen, or choose another language."
      onRetry={onRetry}
    />
  );
}

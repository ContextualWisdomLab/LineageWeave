import { t, tf } from "./i18n";

const RAW_EXCEPTION_PATTERN =
  /traceback|typeerror|referenceerror|keyerror|internal server error|cannot read properties|exception\s*:|at\s+\S+\.(tsx?|py|js)\b/i;

type StatusError = { status: number; message: string };

export function looksLikeRawException(text: string): boolean {
  return RAW_EXCEPTION_PATTERN.test(text);
}

function statusError(err: unknown): StatusError | null {
  if (typeof err !== "object" || err === null) {
    return null;
  }
  if (!("status" in err) || typeof err.status !== "number") {
    return null;
  }
  const message = "message" in err && typeof err.message === "string" ? err.message : "";
  return { status: err.status, message };
}

export function productExceptionCopy(
  err: unknown,
  action: string,
): { title: string; description: string } {
  const backend = statusError(err);
  if (backend && backend.status === 503) {
    return {
      title: `${action} ${t("is temporarily unavailable.")} ${t("Saved evidence is still available.")}`,
      description: t("Retry, or continue with saved evidence."),
    };
  }
  if (backend && backend.status >= 400 && backend.status < 500) {
    const message = backend.message.trim();
    if (!message || looksLikeRawException(message)) {
      return fallbackCopy(action);
    }
    return {
      title: message,
      description: t("Correct the highlighted fields, then retry."),
    };
  }
  if (backend) {
    return fallbackCopy(action);
  }
  return fallbackCopy(action);
}

function fallbackCopy(action: string): { title: string; description: string } {
  return {
    title: tf("{action} could not be completed.", { action }),
    description: t("Retry, or continue with saved evidence."),
  };
}

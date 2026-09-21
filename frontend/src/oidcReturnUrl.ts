export const OIDC_RETURN_URL_STORAGE_KEY = "lineageweave.oidc.returnUrl";
const MAX_OIDC_RETURN_URL_LENGTH = 4096;
const OIDC_RETURN_URL_BASE = "https://lineageweave.invalid";

/** Authorization-endpoint response params appended to the redirect URI.
 * Success responses use `code`/`state`; OAuth error responses may add
 * `error`, `error_description`, and `error_uri` (RFC 6749 sec. 4.1.2/4.1.2.1).
 * `session_state` and `iss` are OIDC/session-response metadata. None belongs
 * in a shareable or retried product return URL. */
const OIDC_CALLBACK_PARAMS = [
  "code",
  "state",
  "session_state",
  "iss",
  "error",
  "error_description",
  "error_uri",
] as const;

/** A correlated callback carries the client-supplied `state` plus a response
 * signal. `state` alone is not sufficient, and response-looking query names
 * without `state` must not let stale auth storage override current product
 * navigation. */
const OIDC_CALLBACK_SIGNAL_PARAMS = [
  "code",
  "session_state",
  "iss",
  "error",
  "error_description",
  "error_uri",
] as const;

/** Removes OIDC callback artifacts from `url` in place -- call before turning
 * `window.location` into a link a user can copy or share. */
export function stripOidcCallbackParams(url: URL): void {
  OIDC_CALLBACK_PARAMS.forEach((param) => url.searchParams.delete(param));
}

type UrlLike = Pick<Location, "pathname" | "search" | "hash">;

function isSafeReturnUrl(value: string): boolean {
  return (
    value.length <= MAX_OIDC_RETURN_URL_LENGTH &&
    value.startsWith("/") &&
    !value.startsWith("//")
  );
}

function sanitizeReturnUrl(value: string): string {
  if (!isSafeReturnUrl(value)) return "";
  const url = new URL(value, OIDC_RETURN_URL_BASE);
  // WHATWG URL parsing treats backslashes as authority separators for special
  // schemes. Reject any value that parses away from the product origin rather
  // than silently re-minting its path as a local deep link.
  if (url.origin !== OIDC_RETURN_URL_BASE) return "";
  stripOidcCallbackParams(url);
  const cleaned = `${url.pathname}${url.search}${url.hash}`;
  return isSafeReturnUrl(cleaned) ? cleaned : "";
}

function isOidcCallbackLocation(location: UrlLike): boolean {
  const params = new URLSearchParams(location.search);
  return (
    params.has("state") &&
    OIDC_CALLBACK_SIGNAL_PARAMS.some((param) => params.has(param))
  );
}

function peekRememberedReturnUrl(): string {
  try {
    const sessionStored = window.sessionStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY) ?? "";
    const fromSession = sanitizeReturnUrl(sessionStored);
    if (fromSession) return fromSession;
  } catch {
    // Fall through to local storage or the current callback location.
  }
  try {
    const localStored = window.localStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY) ?? "";
    return sanitizeReturnUrl(localStored);
  } catch {
    return "";
  }
}

export function returnUrlFromLocation(location: UrlLike = window.location): string {
  // A provider callback is rooted at redirect_uri, so rebuilding a retry URL
  // from that callback alone can erase the deep link remembered before the
  // redirect. Prefer the validated remembered path only for a correlated
  // callback; ordinary product navigation continues to use location.
  if (isOidcCallbackLocation(location)) {
    const remembered = peekRememberedReturnUrl();
    if (remembered) return remembered;
  }

  // A restored return URL can itself be a post-redirect URL still carrying
  // Keycloak callback artifacts (devin review thread on PR #576): strip
  // them here too, so no consumer of this module re-mints a URL with a
  // one-time authorization code in it.
  const value = `${location.pathname}${location.search}${location.hash}`;
  return sanitizeReturnUrl(value) || "/";
}

export function rememberOidcReturnUrl(value: string): void {
  const cleaned = sanitizeReturnUrl(value);
  if (!cleaned) return;
  try {
    window.sessionStorage.setItem(OIDC_RETURN_URL_STORAGE_KEY, cleaned);
  } catch {
    // OIDC state remains the fallback when session storage is unavailable.
  }
  try {
    window.localStorage.setItem(OIDC_RETURN_URL_STORAGE_KEY, cleaned);
  } catch {
    // The OIDC state and session storage remain the fallbacks.
  }
}

function stateReturnUrl(state: unknown): string {
  let candidate = state;
  if (typeof candidate === "string") {
    const cleaned = sanitizeReturnUrl(candidate);
    if (cleaned) return cleaned;
    if (candidate.length > MAX_OIDC_RETURN_URL_LENGTH) return "";
    try {
      candidate = JSON.parse(candidate);
    } catch {
      return "";
    }
  }
  if (typeof candidate !== "object" || candidate === null || !("returnUrl" in candidate)) {
    return "";
  }
  const value = (candidate as { returnUrl?: unknown }).returnUrl;
  return typeof value === "string" ? sanitizeReturnUrl(value) : "";
}

export function restoreOidcReturnUrl(state: unknown): string {
  const fromState = stateReturnUrl(state);
  let sessionStored = "";
  let localStored = "";
  try {
    sessionStored = window.sessionStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY) ?? "";
    window.sessionStorage.removeItem(OIDC_RETURN_URL_STORAGE_KEY);
  } catch {
    // Fall through to local storage or the current path.
  }
  try {
    localStored = window.localStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY) ?? "";
    window.localStorage.removeItem(OIDC_RETURN_URL_STORAGE_KEY);
  } catch {
    // Fall through to the current path.
  }
  if (fromState) return fromState;
  const fromSession = sanitizeReturnUrl(sessionStored);
  if (fromSession) return fromSession;
  const fromLocal = sanitizeReturnUrl(localStored);
  if (fromLocal) return fromLocal;
  return new URLSearchParams(window.location.search).has("post")
    ? returnUrlFromLocation()
    : window.location.pathname;
}

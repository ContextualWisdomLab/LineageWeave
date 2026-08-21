export const OIDC_RETURN_URL_STORAGE_KEY = "lineageweave.oidc.returnUrl";
const MAX_OIDC_RETURN_URL_LENGTH = 4096;

type UrlLike = Pick<Location, "pathname" | "search" | "hash">;

function isSafeReturnUrl(value: string): boolean {
  const hasControlCharacter = [...value].some((character) => {
    const code = character.charCodeAt(0);
    return code <= 0x1f || code === 0x7f;
  });
  return (
    value.length <= MAX_OIDC_RETURN_URL_LENGTH &&
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !value.includes("\\") &&
    !hasControlCharacter
  );
}

export function returnUrlFromLocation(location: UrlLike = window.location): string {
  const value = `${location.pathname}${location.search}${location.hash}`;
  return isSafeReturnUrl(value) ? value : "/";
}

export function rememberOidcReturnUrl(value: string): void {
  if (!isSafeReturnUrl(value)) return;
  try {
    window.sessionStorage.setItem(OIDC_RETURN_URL_STORAGE_KEY, value);
  } catch {
    // OIDC state remains the fallback when session storage is unavailable.
  }
  try {
    window.localStorage.setItem(OIDC_RETURN_URL_STORAGE_KEY, value);
  } catch {
    // The OIDC state and session storage remain the fallbacks.
  }
}

function stateReturnUrl(state: unknown): string {
  let candidate = state;
  if (typeof candidate === "string") {
    if (isSafeReturnUrl(candidate)) return candidate;
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
  return typeof value === "string" && isSafeReturnUrl(value) ? value : "";
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
  if (isSafeReturnUrl(sessionStored)) return sessionStored;
  if (isSafeReturnUrl(localStored)) return localStored;
  return new URLSearchParams(window.location.search).has("post")
    ? returnUrlFromLocation()
    : window.location.pathname;
}

export const OIDC_RETURN_URL_STORAGE_KEY = "lineageweave.oidc.returnUrl";

type UrlLike = Pick<Location, "pathname" | "search" | "hash">;

function isSafeReturnUrl(value: string): boolean {
  return value.startsWith("/") && !value.startsWith("//");
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
}

function stateReturnUrl(state: unknown): string {
  if (typeof state !== "object" || state === null || !("returnUrl" in state)) return "";
  const value = (state as { returnUrl?: unknown }).returnUrl;
  return typeof value === "string" && isSafeReturnUrl(value) ? value : "";
}

export function restoreOidcReturnUrl(state: unknown): string {
  const fromState = stateReturnUrl(state);
  let stored = "";
  try {
    stored = window.sessionStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY) ?? "";
    window.sessionStorage.removeItem(OIDC_RETURN_URL_STORAGE_KEY);
  } catch {
    // Fall through to the current path.
  }
  if (fromState) return fromState;
  if (isSafeReturnUrl(stored)) return stored;
  return new URLSearchParams(window.location.search).has("post")
    ? returnUrlFromLocation()
    : window.location.pathname;
}

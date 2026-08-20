import { beforeEach, describe, expect, it } from "vitest";
import {
  OIDC_RETURN_URL_STORAGE_KEY,
  rememberOidcReturnUrl,
  restoreOidcReturnUrl,
  returnUrlFromLocation,
} from "./oidcReturnUrl";

describe("OIDC deep-link return URL", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    window.history.replaceState({}, "", "/?post=synthetic-post#evidence");
  });

  it("preserves the post query and hash through the OIDC state callback", () => {
    const returnUrl = returnUrlFromLocation();

    expect(returnUrl).toBe("/?post=synthetic-post#evidence");
    expect(restoreOidcReturnUrl({ returnUrl })).toBe(returnUrl);
  });

  it("restores the deep link from storage when the callback has no state", () => {
    const returnUrl = returnUrlFromLocation();
    rememberOidcReturnUrl(returnUrl);

    expect(restoreOidcReturnUrl(undefined)).toBe(returnUrl);
    expect(window.sessionStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY)).toBeNull();
  });
});

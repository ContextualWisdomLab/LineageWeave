import { beforeEach, describe, expect, it } from "vitest";
import {
  rememberOidcReturnUrl,
  restoreOidcReturnUrl,
  returnUrlFromLocation,
} from "./oidcReturnUrl";

describe("OIDC return URL handling", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("keeps a post deep link and rejects external destinations", () => {
    expect(returnUrlFromLocation({ pathname: "/", search: "?post=abc", hash: "" })).toBe(
      "/?post=abc",
    );
    expect(returnUrlFromLocation({ pathname: "//evil.example", search: "", hash: "" })).toBe("/");
  });

  it("restores the deep link from state before falling back to the path", () => {
    rememberOidcReturnUrl("/?post=stored");
    expect(restoreOidcReturnUrl({ returnUrl: "/?post=from-state" })).toBe("/?post=from-state");
    expect(restoreOidcReturnUrl(undefined)).toBe(window.location.pathname);
  });
});

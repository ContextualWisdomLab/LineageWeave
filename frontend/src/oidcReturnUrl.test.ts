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

  it("restores an object or serialized OIDC state before storage fallback", () => {
    rememberOidcReturnUrl("/?post=stored");
    expect(restoreOidcReturnUrl({ returnUrl: "/?post=from-object" })).toBe("/?post=from-object");

    rememberOidcReturnUrl("/?post=stored-again");
    expect(restoreOidcReturnUrl('{"returnUrl":"/?post=from-json"}')).toBe("/?post=from-json");
    expect(window.sessionStorage.getItem("lineageweave.oidc.returnUrl")).toBeNull();
  });
});

import { beforeEach, describe, expect, it } from "vitest";
import {
  rememberOidcReturnUrl,
  restoreOidcReturnUrl,
  returnUrlFromLocation,
  stripOidcCallbackParams,
} from "./oidcReturnUrl";

describe("OIDC return URL handling", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("keeps a post deep link and rejects external destinations", () => {
    expect(returnUrlFromLocation({ pathname: "/", search: "?post=abc", hash: "" })).toBe(
      "/?post=abc",
    );
    expect(returnUrlFromLocation({ pathname: "//evil.example", search: "", hash: "" })).toBe("/");
  });

  it("restores an object or serialized OIDC state before storage fallback", () => {
    rememberOidcReturnUrl("/?post=stored-before-direct");
    expect(restoreOidcReturnUrl("/?post=from-direct-state")).toBe(
      "/?post=from-direct-state",
    );

    rememberOidcReturnUrl("/?post=stored");
    expect(restoreOidcReturnUrl({ returnUrl: "/?post=from-object" })).toBe("/?post=from-object");

    rememberOidcReturnUrl("/?post=stored-again");
    expect(restoreOidcReturnUrl('{"returnUrl":"/?post=from-json"}')).toBe("/?post=from-json");
    expect(window.sessionStorage.getItem("lineageweave.oidc.returnUrl")).toBeNull();
    expect(window.localStorage.getItem("lineageweave.oidc.returnUrl")).toBeNull();
  });

  it("rejects oversized and recursively encoded state without exhausting the stack", () => {
    rememberOidcReturnUrl("/?post=stored-fallback");
    const oversizedNestedState = `${"[".repeat(5000)}0${"]".repeat(5000)}`;

    expect(restoreOidcReturnUrl(oversizedNestedState)).toBe("/?post=stored-fallback");

    rememberOidcReturnUrl("/?post=stored-after-encoded-state");
    const recursivelyEncoded = JSON.stringify(JSON.stringify({ returnUrl: "/?post=nested" }));
    expect(restoreOidcReturnUrl(recursivelyEncoded)).toBe(
      "/?post=stored-after-encoded-state",
    );

    rememberOidcReturnUrl("/?post=stored-after-invalid-json");
    expect(restoreOidcReturnUrl("not-json-state")).toBe(
      "/?post=stored-after-invalid-json",
    );
  });

  it("rejects oversized direct paths before storing or restoring them", () => {
    const oversizedPath = `/?post=${"a".repeat(4096)}`;

    rememberOidcReturnUrl(oversizedPath);

    expect(window.sessionStorage.getItem("lineageweave.oidc.returnUrl")).toBeNull();
    expect(restoreOidcReturnUrl({ returnUrl: oversizedPath })).toBe("/");
  });

  it("restores a deep link from local storage when session storage is empty", () => {
    window.localStorage.setItem("lineageweave.oidc.returnUrl", "/?post=from-local-storage");

    expect(restoreOidcReturnUrl(undefined)).toBe("/?post=from-local-storage");
    expect(window.localStorage.getItem("lineageweave.oidc.returnUrl")).toBeNull();
  });
});

describe("stripOidcCallbackParams", () => {
  it("removes the Keycloak auth-exchange params but keeps app deep-link params", () => {
    const url = new URL(
      "http://localhost:15173/?state=abc&session_state=def&iss=http%3A%2F%2Fidp&code=xyz&post=post-1&workspace=board",
    );

    stripOidcCallbackParams(url);

    expect(url.searchParams.get("state")).toBeNull();
    expect(url.searchParams.get("session_state")).toBeNull();
    expect(url.searchParams.get("iss")).toBeNull();
    expect(url.searchParams.get("code")).toBeNull();
    expect(url.searchParams.get("post")).toBe("post-1");
    expect(url.searchParams.get("workspace")).toBe("board");
  });

  it("is a no-op when no OIDC params are present", () => {
    const url = new URL("http://localhost:15173/?post=post-1");

    stripOidcCallbackParams(url);

    expect(url.toString()).toBe("http://localhost:15173/?post=post-1");
  });
});

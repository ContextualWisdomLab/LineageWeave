// @vitest-environment node
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { describe, expect, it, vi } from "vitest";

const syntheticToken = "synthetic-authorized-bearer";
const sensitiveResponse = "synthetic-private-response-marker";

function harness(kind: "http" | "mcp", token: string | null, env: Record<string, string> = {}) {
  const targetSource = readFileSync(new URL("../../scripts/k6_target.js", import.meta.url), "utf8")
    .replaceAll("export function", "function");
  const source = readFileSync(
    new URL(`../../scripts/k6_${kind}_e2e.js`, import.meta.url),
    "utf8",
  ).replace(/^import .*;$/gm, "")
    .replace("export default function", "function run")
    .replaceAll("export function", "function");
  const post = vi.fn<(url: string, body: unknown, params: { headers: Record<string, string> }) => { status: number; body: string; timings: { duration: number } }>(() => ({
    status: 401,
    body: sensitiveResponse,
    timings: { duration: 1 },
  }));
  const open = vi.fn(() => token);
  const abort = vi.fn((message: string) => { throw new Error(message); });
  const api = runInNewContext(`${targetSource}\n${source}\n({ authenticate, setup, run${kind === "mcp" ? ", result, structured" : ""} });`, {
    __ENV: {
      REQUEST_TIMEOUT: "20s",
      ...(token === null ? {} : { K6_ACCESS_TOKEN_FILE: "/synthetic/runtime-token" }),
      ...env,
    },
    open,
    exec: { test: { abort } },
    http: { post },
    fail: (message: string) => { throw new Error(message); },
    check: () => false,
    Counter: class { add() {} },
    Trend: class { add() {} },
  });
  return { api, post, open, abort };
}

describe.each(["http", "mcp"] as const)("%s k6 authentication", (kind) => {
  it("uses an operator-supplied token without a password-grant request", () => {
    const { api, post, open } = harness(kind, ` ${syntheticToken}\n`);
    expect(api.authenticate()).toBe(syntheticToken);
    expect(open).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
    expect(() => api.setup()).toThrow(/HTTP 401/);
    expect(post).toHaveBeenCalledTimes(1);
    expect(post.mock.calls[0][0]).not.toContain("openid-connect/token");
    expect(post.mock.calls[0][2].headers.Authorization).toBe(`Bearer ${syntheticToken}`);
    expect(post.mock.calls[0][2]).toHaveProperty("redirects", 0);
  });

  it("rejects an empty supplied token before any authenticated request", () => {
    const { api, post } = harness(kind, " \n");
    expect(() => api.setup()).toThrow(/obtain a fresh authorized token/);
    expect(post).not.toHaveBeenCalled();
  });

  it("does not fall back to a password grant after a supplied token expires", () => {
    const { api, post, abort } = harness(kind, syntheticToken);
    expect(() => api.authenticate(true)).toThrow(/obtain a fresh authorized token/);
    expect(abort).toHaveBeenCalledTimes(1);
    expect(post).not.toHaveBeenCalled();
  });

  it("retains the explicit synthetic realm authentication path", () => {
    const { api, post, open } = harness(kind, null);
    expect(() => api.authenticate()).toThrow(/HTTP 401/);
    expect(post.mock.calls[0][0]).toContain("openid-connect/token");
    expect(open).not.toHaveBeenCalled();
    expect(post.mock.calls[0][2]).toHaveProperty("redirects", 0);
  });

  it.each([
    "http://remote.example.test", "http://localhost.evil.test", "http://127.0.0.1@evil.test",
    "http://127.0.0.1\\@evil.test", "http://[::1].evil.test", "ftp://localhost",
    "https://user:synthetic-secret@remote.example.test", "https://remote.example.test\\@evil.test",
  ])("rejects unsafe target %s before credential reading or network I/O", (target) => {
    expect(() => harness(kind, syntheticToken, {
      [kind === "http" ? "BACKEND_URL" : "MCP_URL"]: target,
    })).toThrow(/requires HTTPS or HTTP on an exact loopback host/);
  });

  it.each(["https://remote.example.test/api", "http://127.0.0.1:18420", "http://[::1]:18001/mcp"])(
    "allows declared secure or loopback target %s", (target) => {
      const { api, post } = harness(kind, syntheticToken, {
        [kind === "http" ? "BACKEND_URL" : "MCP_URL"]: target,
      });
      expect(() => api.setup()).toThrow(/HTTP 401/);
      expect(post.mock.calls[0][0]).toContain(target);
    },
  );

  it("rejects remote HTTP identity authentication before network I/O", () => {
    expect(() => harness(kind, null, { KEYCLOAK_URL: "http://remote.example.test" }))
      .toThrow(/KEYCLOAK_URL requires HTTPS/);
  });

  it("ignores an unused identity endpoint when a runtime token is supplied", () => {
    const { api, post } = harness(kind, syntheticToken, { KEYCLOAK_URL: "http://remote.example.test" });
    expect(api.authenticate()).toBe(syntheticToken);
    expect(post).not.toHaveBeenCalled();
  });

  it("keeps rejection diagnostics free of response content and bearer tokens", () => {
    const { api } = harness(kind, syntheticToken);
    try {
      api.setup();
      throw new Error("expected rejection");
    } catch (error) {
      expect(String(error)).toContain("HTTP 401");
      expect(String(error)).not.toContain(sensitiveResponse);
      expect(String(error)).not.toContain(syntheticToken);
    }
  });
});

it.each(["rpc", "tool"])("MCP %s errors omit untrusted server content", (kind) => {
  const { api } = harness("mcp", syntheticToken);
  const response = {
    status: 200,
    body: `data: ${JSON.stringify(kind === "rpc"
      ? { error: { message: sensitiveResponse } }
      : { result: { isError: true, content: [{ text: sensitiveResponse }] } })}\n`,
  };
  expect(() => kind === "rpc" ? api.result(response) : api.structured(response))
    .toThrow(/HTTP 200/);
  try {
    if (kind === "rpc") api.result(response);
    else api.structured(response);
  } catch (error) {
    expect(String(error)).not.toContain(sensitiveResponse);
  }
});

it("malformed MCP JSON cannot enter parser diagnostics", () => {
  const { api } = harness("mcp", syntheticToken);
  const response = { status: 200, body: `data: ${sensitiveResponse}\n` };
  expect(() => api.result(response)).toThrow("MCP returned malformed JSON: HTTP 200");
});

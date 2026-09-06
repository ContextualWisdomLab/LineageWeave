// @vitest-environment node
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";

const privatePayload = "synthetic-private-response-marker";

function harness(name: string) {
  const source = readFileSync(new URL(`../../scripts/${name}`, import.meta.url), "utf8")
    .replace(/^import .*;$/gm, "")
    .replace(/export default function/g, "function iteration")
    .replace(/export function/g, "function");
  const post = () => ({
    status: 503,
    body: privatePayload,
    timings: { duration: 1 },
  });
  const context = {
    __ENV: { REQUEST_TIMEOUT: "1s" },
    http: { post },
    check: () => true,
    fail: (message: string) => { throw new Error(message); },
    Counter: class { add() {} },
    Trend: class { add() {} },
  };
  return runInNewContext(`${source}\n({ setup, ${name.includes("mcp") ? "result, structured" : ""} })`, context);
}

describe("k6 diagnostic confidentiality", () => {
  it("omits a rejected Ask response body", () => {
    const source = readFileSync(new URL("../../scripts/k6_http_e2e.js", import.meta.url), "utf8")
      .replace(/^import .*;$/gm, "")
      .replace(/export default function/g, "function iteration")
      .replace(/export function/g, "function");
    let calls = 0;
    const setup = runInNewContext(`${source}\nsetup`, {
      __ENV: { REQUEST_TIMEOUT: "1s" },
      http: { post: () => ++calls === 1
        ? { status: 200, json: () => "synthetic-token" }
        : { status: 503, body: privatePayload, timings: { duration: 1 } } },
      fail: (message: string) => { throw new Error(message); },
      Counter: class { add() {} },
      Trend: class { add() {} },
    });
    expect(setup).toThrow(/^synthetic Ask enqueue failed with HTTP 503$/);
    expect(calls).toBe(2);
  });

  it("omits JSON-RPC error details", () => {
    expect(() => harness("k6_mcp_e2e.js").result({
      status: 200,
      body: `data: ${JSON.stringify({ error: { message: privatePayload } })}`,
    })).toThrow(/^MCP request failed: HTTP 200$/);
  });

  it("omits failed tool content", () => {
    expect(() => harness("k6_mcp_e2e.js").structured({
      status: 200,
      body: `data: ${JSON.stringify({ result: { isError: true, content: privatePayload } })}`,
    })).toThrow(/^MCP tool failed: HTTP 200$/);
  });

  it("contains malformed JSON without exposing the parser excerpt", () => {
    expect(() => harness("k6_mcp_e2e.js").result({
      status: 200, body: `data: ${privatePayload}`,
    })).toThrow(/^MCP response was unreadable: HTTP 200$/);
  });

  it("preserves successful structured evidence", () => {
    const payload = { ask_job_id: "synthetic-job", job_status_code: "queued" };
    expect(harness("k6_mcp_e2e.js").structured({
      status: 200,
      body: `data: ${JSON.stringify({ result: { structuredContent: payload } })}`,
    })).toEqual(payload);
  });

  it.each([null, [], "synthetic-private-response-marker", 7].map(value => [value]))("rejects invalid envelopes (%j)", (envelope) => {
    expect(() => harness("k6_mcp_e2e.js").result({
      status: 200, body: `data: ${JSON.stringify(envelope)}`,
    })).toThrow(/^MCP response envelope was invalid: HTTP 200$/);
  });

  it("rejects an envelope without a result", () => {
    expect(() => harness("k6_mcp_e2e.js").result({
      status: 200, body: "data: {}",
    })).toThrow(/^MCP response omitted result: HTTP 200$/);
  });

  it.each([null, [], privatePayload].map(value => [value]))("rejects invalid tool results (%j)", (result) => {
    expect(() => harness("k6_mcp_e2e.js").structured({
      status: 200, body: `data: ${JSON.stringify({ result })}`,
    })).toThrow(/^MCP tool result was invalid: HTTP 200$/);
  });

  it.each([undefined, null, [], privatePayload].map(value => [value]))("rejects invalid structured content (%j)", (structuredContent) => {
    expect(() => harness("k6_mcp_e2e.js").structured({
      status: 200, body: `data: ${JSON.stringify({ result: { structuredContent } })}`,
    })).toThrow(/^MCP structured content was invalid: HTTP 200$/);
  });

  it("contains a missing response body", () => {
    expect(() => harness("k6_mcp_e2e.js").result({ status: 0, body: null }))
      .toThrow(/^MCP response omitted a data event: HTTP 0$/);
  });
});

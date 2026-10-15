/** Measure authenticated MCP responsiveness against synthetic durable Ask data. */

import http from "k6/http";
import exec from "k6/execution";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";
import { credentialTarget } from "./k6_target.js";

const mcpUrl = credentialTarget(__ENV.MCP_URL || "http://localhost:18001/mcp", "MCP_URL");
const requestTimeout = __ENV.REQUEST_TIMEOUT;
if (!__ENV.K6_ACCESS_TOKEN_FILE) {
  throw new Error("K6_ACCESS_TOKEN_FILE is required for an authorized synthetic load run");
}
const suppliedToken = open(__ENV.K6_ACCESS_TOKEN_FILE).trim();
if (!suppliedToken) {
  throw new Error("K6_ACCESS_TOKEN_FILE is empty; obtain a fresh authorized token");
}
const protocolVersion = "2025-11-25";
const unitlessDuration = /^\d+(?:\.\d+)?$/;

const initializeDuration = new Trend("lineageweave_mcp_initialize_duration", true);
const submitDuration = new Trend("lineageweave_mcp_submit_duration", true);
const readDuration = new Trend("lineageweave_mcp_read_duration", true);
const jobStateObservations = new Counter("lineageweave_mcp_job_state_observations");

let vuToken;
let vuSession;

function result(response) {
  const line = response.body.split("\n").find((entry) => entry.startsWith("data: "));
  if (!line) fail(`MCP response omitted a data event: HTTP ${response.status}`);
  let envelope;
  try {
    envelope = JSON.parse(line.slice(6));
  } catch {
    fail(`MCP returned malformed JSON: HTTP ${response.status}`);
  }
  if (envelope.error) fail(`MCP returned an error: HTTP ${response.status}`);
  return envelope.result;
}

function request(token, session, id, method, params) {
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": protocolVersion,
  };
  if (session) headers["Mcp-Session-Id"] = session;
  const envelope = id === null
    ? { jsonrpc: "2.0", method, params }
    : { jsonrpc: "2.0", id, method, params };
  return http.post(
    mcpUrl,
    JSON.stringify(envelope),
    { headers, tags: { endpoint: method }, timeout: requestTimeout, redirects: 0 },
  );
}

function initialize(token) {
  const response = request(token, null, 1, "initialize", {
    protocolVersion,
    capabilities: {},
    clientInfo: { name: "lineageweave-k6", version: "1" },
  });
  initializeDuration.add(response.timings.duration);
  if (response.status !== 200) fail(`MCP initialize failed with HTTP ${response.status}`);
  result(response);
  const session = response.headers["Mcp-Session-Id"];
  if (!session) fail("MCP initialize omitted Mcp-Session-Id");
  const initialized = request(token, session, null, "notifications/initialized", undefined);
  if (initialized.status !== 202) fail(`MCP initialized notification failed with HTTP ${initialized.status}`);
  return session;
}

function callTool(token, session, id, name, args) {
  return request(token, session, id, "tools/call", { name, arguments: args });
}

function structured(response) {
  const toolResult = result(response);
  if (toolResult.isError) fail(`MCP tool failed: HTTP ${response.status}`);
  return toolResult.structuredContent;
}

export function setup() {
  if (!requestTimeout) fail("REQUEST_TIMEOUT is required");
  if (unitlessDuration.test(requestTimeout)) fail("REQUEST_TIMEOUT must include a duration unit, for example 20s");
  const token = suppliedToken;
  const session = initialize(token);
  const response = callTool(token, session, 2, "submit_global_ask", {
    question: "Summarize the authorized synthetic evidence.",
  });
  submitDuration.add(response.timings.duration);
  if (response.status !== 200) fail(`MCP Ask submit failed with HTTP ${response.status}`);
  return { token, askJobId: structured(response).ask_job_id };
}

export default function (data) {
  vuToken ||= data.token;
  vuSession ||= initialize(vuToken);
  const response = callTool(vuToken, vuSession, 3, "read_global_ask_job", { ask_job_id: data.askJobId });
  if (response.status === 401) {
    exec.test.abort("Authorized access token expired; obtain a fresh token and rerun");
  }
  readDuration.add(response.timings.duration);
  const ok = check(response, { "MCP Ask read succeeds": (item) => item.status === 200 });
  if (ok) {
    const payload = structured(response);
    jobStateObservations.add(1, { job_status: String(payload.job_status_code || "unknown") });
  }
}

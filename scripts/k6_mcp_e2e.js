/** Measure authenticated MCP responsiveness against synthetic durable Ask data. */

import http from "k6/http";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";

const mcpUrl = __ENV.MCP_URL || "http://localhost:18001/mcp";
const keycloakUrl = (__ENV.KEYCLOAK_URL || "http://localhost:18080").replace(/\/$/, "");
const realm = __ENV.KEYCLOAK_REALM || "lineageweave-demo";
const clientId = __ENV.KEYCLOAK_CLIENT_ID || "lineageweave-frontend";
const username = __ENV.K6_USERNAME || "demo.analyst";
const password = __ENV.K6_PASSWORD || "lineageweave-demo-only";
const requestTimeout = __ENV.REQUEST_TIMEOUT;
const keycloakHost = __ENV.KEYCLOAK_HOST;
const protocolVersion = "2025-11-25";
const unitlessDuration = /^\d+(?:\.\d+)?$/;
// Persisted Global Ask states: migrations/0165_global_ask_job.sql.
const jobStates = new Set(["queued", "running", "succeeded", "failed"]);

const initializeDuration = new Trend("lineageweave_mcp_initialize_duration", true);
const submitDuration = new Trend("lineageweave_mcp_submit_duration", true);
const readDuration = new Trend("lineageweave_mcp_read_duration", true);
const jobStateObservations = new Counter("lineageweave_mcp_job_state_observations");

let vuToken;
let vuSession;

function authenticate() {
  const headers = keycloakHost ? { Host: keycloakHost } : {};
  const response = http.post(
    `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`,
    { grant_type: "password", client_id: clientId, username, password },
    { headers, tags: { endpoint: "oidc_token" }, timeout: requestTimeout },
  );
  if (response.status !== 200) fail(`synthetic OIDC login failed with HTTP ${response.status}`);
  return response.json("access_token");
}

function result(response, expectedId) {
  const line = typeof response.body === "string"
    ? response.body.split("\n").find((entry) => entry.startsWith("data: "))
    : undefined;
  if (!line) fail(`MCP response omitted a data event: HTTP ${response.status}`);
  let envelope;
  try {
    envelope = JSON.parse(line.slice(6));
  } catch {
    fail(`MCP response was unreadable: HTTP ${response.status}`);
  }
  if (!envelope || typeof envelope !== "object" || Array.isArray(envelope)) {
    fail(`MCP response envelope was invalid: HTTP ${response.status}`);
  }
  if (envelope.jsonrpc !== "2.0") {
    fail(`MCP response protocol was invalid: HTTP ${response.status}`);
  }
  if (!Object.prototype.hasOwnProperty.call(envelope, "id") || envelope.id !== expectedId) {
    fail(`MCP response id mismatch: HTTP ${response.status}`);
  }
  const hasResult = Object.prototype.hasOwnProperty.call(envelope, "result");
  const hasError = Object.prototype.hasOwnProperty.call(envelope, "error");
  if (hasResult === hasError) {
    fail(`MCP response result/error shape was invalid: HTTP ${response.status}`);
  }
  if (hasError) fail(`MCP request failed: HTTP ${response.status}`);
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
    { headers, tags: { endpoint: method }, timeout: requestTimeout },
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
  result(response, 1);
  const session = response.headers["Mcp-Session-Id"];
  if (!session) fail("MCP initialize omitted Mcp-Session-Id");
  const initialized = request(token, session, null, "notifications/initialized", undefined);
  if (initialized.status !== 202) fail(`MCP initialized notification failed with HTTP ${initialized.status}`);
  return session;
}

function callTool(token, session, id, name, args) {
  return request(token, session, id, "tools/call", { name, arguments: args });
}

function structured(response, expectedId) {
  const toolResult = result(response, expectedId);
  if (!toolResult || typeof toolResult !== "object" || Array.isArray(toolResult)) {
    fail(`MCP tool result was invalid: HTTP ${response.status}`);
  }
  if (toolResult.isError) fail(`MCP tool failed: HTTP ${response.status}`);
  const content = toolResult.structuredContent;
  if (!content || typeof content !== "object" || Array.isArray(content)) {
    fail(`MCP structured content was invalid: HTTP ${response.status}`);
  }
  return content;
}

export function setup() {
  if (!requestTimeout) fail("REQUEST_TIMEOUT is required");
  if (unitlessDuration.test(requestTimeout)) fail("REQUEST_TIMEOUT must include a duration unit, for example 20s");
  const token = authenticate();
  const session = initialize(token);
  const response = callTool(token, session, 2, "submit_global_ask", {
    question: "Summarize the authorized synthetic evidence.",
  });
  submitDuration.add(response.timings.duration);
  if (response.status !== 200) fail(`MCP Ask submit failed with HTTP ${response.status}`);
  return { token, askJobId: structured(response, 2).ask_job_id };
}

export default function (data) {
  vuToken ||= data.token;
  vuSession ||= initialize(vuToken);
  let response = callTool(vuToken, vuSession, 3, "read_global_ask_job", { ask_job_id: data.askJobId });
  if (response.status === 401) {
    vuToken = authenticate();
    vuSession = initialize(vuToken);
    response = callTool(vuToken, vuSession, 3, "read_global_ask_job", { ask_job_id: data.askJobId });
  }
  readDuration.add(response.timings.duration);
  const ok = check(response, { "MCP Ask read succeeds": (item) => item.status === 200 });
  if (ok) {
    const payload = structured(response, 3);
    check(payload.job_status_code, { "MCP Ask state is declared": (value) => jobStates.has(value) });
    jobStateObservations.add(1, { job_status: jobStates.has(payload.job_status_code) ? payload.job_status_code : "unknown" });
  }
}

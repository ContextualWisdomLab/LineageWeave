/** Measure authenticated MCP responsiveness against synthetic durable Ask data.
 *
 * Two explicitly named protocol lanes share one script:
 *  - the default modern stateless lane (`MCP_PROTOCOL_VERSION=2026-07-28`):
 *    every request is self-contained, carries the per-request envelope and the
 *    `Mcp-Method`/`Mcp-Name` routing headers, and needs no `initialize`
 *    handshake or `Mcp-Session-Id`;
 *  - the legacy handshake lane (`MCP_PROTOCOL_VERSION=2025-11-25`) retained as
 *    a compatibility regression for older clients; it is the same harness,
 *    selected by name through that environment variable rather than a copy.
 */

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
const protocolVersion = __ENV.MCP_PROTOCOL_VERSION || "2026-07-28";
const HANDSHAKE_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"];
const isModern = !HANDSHAKE_VERSIONS.includes(protocolVersion);
const unitlessDuration = /^\d+(?:\.\d+)?$/;

const initializeDuration = new Trend("lineageweave_mcp_initialize_duration", true);
const submitDuration = new Trend("lineageweave_mcp_submit_duration", true);
const readDuration = new Trend("lineageweave_mcp_read_duration", true);
const jobStateObservations = new Counter("lineageweave_mcp_job_state_observations");

let vuToken;
let vuSession;

/** Authenticate the synthetic buyer principal through the configured Keycloak boundary. */
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

/** Accept only the JSON-RPC response that belongs to the current observation. */
function result(response, expectedId) {
  const line = response.body.split("\n").find((entry) => entry.startsWith("data: "));
  const envelope = line ? JSON.parse(line.slice(6)) : response.json();
  if (envelope.jsonrpc !== "2.0" || envelope.id !== expectedId) {
    fail(`MCP reply identity mismatch: HTTP ${response.status}`);
  }
  const hasResult = envelope.result !== undefined;
  const hasError = envelope.error !== undefined;
  if (hasResult === hasError) {
    fail(`MCP reply must carry exactly one of result or error: HTTP ${response.status}`);
  }
  if (hasError) fail(`MCP returned error code ${envelope.error.code}: HTTP ${response.status}`);
  return envelope.result;
}

/** Build the self-describing metadata required by the 2026-07-28 stateless lane. */
function modernMeta() {
  return {
    "io.modelcontextprotocol/protocolVersion": protocolVersion,
    "io.modelcontextprotocol/clientCapabilities": {},
  };
}

/** Send one generic MCP request while preserving the selected protocol-era contract. */
function request(token, session, id, method, params) {
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": protocolVersion,
  };
  if (isModern) headers["Mcp-Method"] = method;
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

/** Establish only the legacy handshake-era worker-local MCP session. */
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

/** Call one durable Global Ask tool without duplicating modern and legacy harnesses. */
function callTool(token, session, id, name, args) {
  if (isModern) {
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: "application/json, text/event-stream",
      "Content-Type": "application/json",
      "MCP-Protocol-Version": protocolVersion,
      "Mcp-Method": "tools/call",
      "Mcp-Name": name,
    };
    const envelope = {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: { name, arguments: args, _meta: modernMeta() },
    };
    return http.post(
      mcpUrl,
      JSON.stringify(envelope),
      { headers, tags: { endpoint: "tools/call" }, timeout: requestTimeout },
    );
  }
  return request(token, session, id, "tools/call", { name, arguments: args });
}

/** Return structured tool content only after transport and tool-level error checks. */
function structured(response, expectedId) {
  const toolResult = result(response, expectedId);
  if (toolResult.isError) fail(`MCP tool returned an error result: HTTP ${response.status}`);
  return toolResult.structuredContent;
}

/** Seed one durable synthetic Ask job and expose only its identifier to VUs. */
export function setup() {
  if (!requestTimeout) fail("REQUEST_TIMEOUT is required");
  if (unitlessDuration.test(requestTimeout)) fail("REQUEST_TIMEOUT must include a duration unit, for example 20s");
  const token = authenticate();
  const session = isModern ? null : initialize(token);
  const response = callTool(token, session, 2, "submit_global_ask", {
    question: "Summarize the authorized synthetic evidence.",
  });
  submitDuration.add(response.timings.duration);
  if (response.status !== 200) fail(`MCP Ask submit failed with HTTP ${response.status}`);
  return { token, askJobId: structured(response, 2).ask_job_id };
}

/** Repeatedly read the durable Ask job while measuring authenticated transport latency. */
export default function (data) {
  vuToken ||= data.token;
  vuSession ||= isModern ? null : initialize(vuToken);
  let response = callTool(vuToken, vuSession, 3, "read_global_ask_job", { ask_job_id: data.askJobId });
  if (response.status === 401) {
    vuToken = authenticate();
    vuSession = isModern ? null : initialize(vuToken);
    response = callTool(vuToken, vuSession, 3, "read_global_ask_job", { ask_job_id: data.askJobId });
  }
  readDuration.add(response.timings.duration);
  const ok = check(response, { "MCP Ask read succeeds": (item) => item.status === 200 });
  if (ok) {
    const payload = structured(response, 3);
    jobStateObservations.add(1, { job_status: String(payload.job_status_code || "unknown") });
  }
}

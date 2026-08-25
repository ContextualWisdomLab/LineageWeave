/**
 * Measure authenticated HTTP responsiveness while one synthetic Ask job runs.
 *
 * This is an observation harness, not a release gate: it defines no latency,
 * error-rate, or throughput threshold. The operator supplies concurrency and
 * duration for the environment being measured.
 */

import http from "k6/http";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";

const backendUrl = (__ENV.BACKEND_URL || "http://localhost:18420").replace(/\/$/, "");
const keycloakUrl = (__ENV.KEYCLOAK_URL || "http://localhost:18080").replace(/\/$/, "");
const realm = __ENV.KEYCLOAK_REALM || "lineageweave-demo";
const clientId = __ENV.KEYCLOAK_CLIENT_ID || "lineageweave-frontend";
const username = __ENV.K6_USERNAME || "demo.analyst";
const password = __ENV.K6_PASSWORD || "lineageweave-demo-only";

const askEnqueueDuration = new Trend("lineageweave_ask_enqueue_duration", true);
const readDuration = new Trend("lineageweave_read_duration", true);
const askPollDuration = new Trend("lineageweave_ask_poll_duration", true);
const askStateObservations = new Counter("lineageweave_ask_state_observations");

let vuToken;

function authenticate() {
  const response = http.post(
    `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`,
    {
      grant_type: "password",
      client_id: clientId,
      username,
      password,
    },
    { tags: { endpoint: "oidc_token" } },
  );
  if (response.status !== 200) {
    fail(`synthetic OIDC login failed with HTTP ${response.status}`);
  }
  return response.json("access_token");
}

function readBatch(token, askJobId) {
  const params = { headers: { Authorization: `Bearer ${token}` } };
  return http.batch([
    ["GET", `${backendUrl}/api/posts`, null, { ...params, tags: { endpoint: "posts" } }],
    ["GET", `${backendUrl}/api/lineage`, null, { ...params, tags: { endpoint: "lineage" } }],
    ["GET", `${backendUrl}/api/dashboard`, null, { ...params, tags: { endpoint: "dashboard" } }],
    [
      "GET",
      `${backendUrl}/api/ask/jobs/${askJobId}`,
      null,
      { ...params, tags: { endpoint: "ask_poll" } },
    ],
  ]);
}

export function setup() {
  const token = authenticate();
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const submitted = http.post(
    `${backendUrl}/api/ask`,
    JSON.stringify({ question: "Summarize the synthetic demo lineage evidence." }),
    { headers, tags: { endpoint: "ask_enqueue" } },
  );
  askEnqueueDuration.add(submitted.timings.duration);
  if (submitted.status !== 202) {
    fail(`synthetic Ask enqueue failed with HTTP ${submitted.status}: ${submitted.body}`);
  }
  return { token, askJobId: submitted.json("ask_job_id") };
}

export default function (data) {
  vuToken ||= data.token;
  let responses = readBatch(vuToken, data.askJobId);
  if (responses.some((response) => response.status === 401)) {
    vuToken = authenticate();
    responses = readBatch(vuToken, data.askJobId);
  }

  readDuration.add(responses[0].timings.duration, { endpoint: "posts" });
  readDuration.add(responses[1].timings.duration, { endpoint: "lineage" });
  readDuration.add(responses[2].timings.duration, { endpoint: "dashboard" });
  askPollDuration.add(responses[3].timings.duration);
  if (responses[3].status === 200) {
    askStateObservations.add(1, {
      job_status: String(responses[3].json("job_status_code") || "unknown"),
    });
  }
  check(responses[0], { "posts read succeeds": (response) => response.status === 200 });
  check(responses[1], { "lineage read succeeds": (response) => response.status === 200 });
  check(responses[2], { "dashboard read succeeds": (response) => response.status === 200 });
  check(responses[3], { "Ask poll succeeds": (response) => response.status === 200 });
}

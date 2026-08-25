/**
 * Measure authenticated HTTP responsiveness while one synthetic Ask job runs.
 *
 * This is an observation harness, not a release gate: it defines no latency,
 * error-rate, or throughput threshold. The operator supplies concurrency and
 * duration for the environment being measured.
 */

import http from "k6/http";
import { check, fail } from "k6";
import { Trend } from "k6/metrics";

const backendUrl = (__ENV.BACKEND_URL || "http://localhost:18420").replace(/\/$/, "");
const keycloakUrl = (__ENV.KEYCLOAK_URL || "http://localhost:18080").replace(/\/$/, "");
const realm = __ENV.KEYCLOAK_REALM || "lineageweave-demo";
const clientId = __ENV.KEYCLOAK_CLIENT_ID || "lineageweave-frontend";
const username = __ENV.K6_USERNAME || "demo.analyst";
const password = __ENV.K6_PASSWORD || "lineageweave-demo-only";

const askEnqueueDuration = new Trend("lineageweave_ask_enqueue_duration", true);
const readDuration = new Trend("lineageweave_read_duration", true);
const askPollDuration = new Trend("lineageweave_ask_poll_duration", true);

export function setup() {
  const tokenResponse = http.post(
    `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`,
    {
      grant_type: "password",
      client_id: clientId,
      username,
      password,
    },
    { tags: { endpoint: "oidc_token" } },
  );
  if (tokenResponse.status !== 200) {
    fail(`synthetic OIDC login failed with HTTP ${tokenResponse.status}`);
  }

  const token = tokenResponse.json("access_token");
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
  const params = { headers: { Authorization: `Bearer ${data.token}` } };
  const responses = http.batch([
    ["GET", `${backendUrl}/api/posts`, null, { ...params, tags: { endpoint: "posts" } }],
    ["GET", `${backendUrl}/api/lineage`, null, { ...params, tags: { endpoint: "lineage" } }],
    [
      "GET",
      `${backendUrl}/api/ask/jobs/${data.askJobId}`,
      null,
      { ...params, tags: { endpoint: "ask_poll" } },
    ],
  ]);

  readDuration.add(responses[0].timings.duration, { endpoint: "posts" });
  readDuration.add(responses[1].timings.duration, { endpoint: "lineage" });
  askPollDuration.add(responses[2].timings.duration);
  check(responses[0], { "posts read succeeds": (response) => response.status === 200 });
  check(responses[1], { "lineage read succeeds": (response) => response.status === 200 });
  check(responses[2], { "Ask poll succeeds": (response) => response.status === 200 });
}

/**
 * Measure authenticated HTTP responsiveness while one synthetic Ask job runs.
 *
 * This is an observation harness, not a release gate: it defines no latency,
 * error-rate, or throughput threshold. The operator supplies concurrency and
 * duration for the environment being measured.
 */

import http from "k6/http";
import exec from "k6/execution";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";
import { credentialTarget } from "./k6_target.js";

const backendUrl = credentialTarget(__ENV.BACKEND_URL || "http://localhost:18420", "BACKEND_URL").replace(/\/$/, "");
const requestTimeout = __ENV.REQUEST_TIMEOUT;
if (!__ENV.K6_ACCESS_TOKEN_FILE) {
  throw new Error("K6_ACCESS_TOKEN_FILE is required for an authorized synthetic load run");
}
const suppliedToken = open(__ENV.K6_ACCESS_TOKEN_FILE).trim();
if (!suppliedToken) {
  throw new Error("K6_ACCESS_TOKEN_FILE is empty; obtain a fresh authorized token");
}
const unitlessDuration = /^\d+(?:\.\d+)?$/;

const askEnqueueDuration = new Trend("lineageweave_ask_enqueue_duration", true);
const readDuration = new Trend("lineageweave_read_duration", true);
const askPollDuration = new Trend("lineageweave_ask_poll_duration", true);
const askStateObservations = new Counter("lineageweave_ask_state_observations");

let vuToken;

function readBatch(token, askJobId) {
  const params = { headers: { Authorization: `Bearer ${token}` }, redirects: 0 };
  return http.batch([
    [
      "GET",
      `${backendUrl}/api/posts`,
      null,
      { ...params, tags: { endpoint: "posts" }, timeout: requestTimeout },
    ],
    [
      "GET",
      `${backendUrl}/api/lineage`,
      null,
      { ...params, tags: { endpoint: "lineage" }, timeout: requestTimeout },
    ],
    [
      "GET",
      `${backendUrl}/api/ask/jobs/${askJobId}`,
      null,
      { ...params, tags: { endpoint: "ask_poll" }, timeout: requestTimeout },
    ],
  ]);
}

export function setup() {
  if (!requestTimeout) {
    fail("REQUEST_TIMEOUT is required");
  }
  if (unitlessDuration.test(requestTimeout)) {
    fail("REQUEST_TIMEOUT must include a duration unit, for example 20s");
  }
  const token = suppliedToken;
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const submitted = http.post(
    `${backendUrl}/api/ask`,
    JSON.stringify({ question: "Summarize the synthetic demo lineage evidence." }),
    { headers, tags: { endpoint: "ask_enqueue" }, timeout: requestTimeout, redirects: 0 },
  );
  askEnqueueDuration.add(submitted.timings.duration);
  if (submitted.status !== 202) {
    fail(`synthetic Ask enqueue failed with HTTP ${submitted.status}`);
  }
  return { token, askJobId: submitted.json("ask_job_id") };
}

export default function (data) {
  vuToken ||= data.token;
  const responses = readBatch(vuToken, data.askJobId);
  if (responses.some((response) => response.status === 401)) {
    exec.test.abort("Authorized access token expired; obtain a fresh token and rerun");
  }

  readDuration.add(responses[0].timings.duration, { endpoint: "posts" });
  readDuration.add(responses[1].timings.duration, { endpoint: "lineage" });
  askPollDuration.add(responses[2].timings.duration);
  if (responses[2].status === 200) {
    askStateObservations.add(1, {
      job_status: String(responses[2].json("job_status_code") || "unknown"),
    });
  }
  check(responses[0], { "posts read succeeds": (response) => response.status === 200 });
  check(responses[1], { "lineage read succeeds": (response) => response.status === 200 });
  check(responses[2], { "Ask poll succeeds": (response) => response.status === 200 });
}

/** Observe authenticated Dashboard reads without invoking an LLM provider. */

import { check, fail } from "k6";
import http from "k6/http";
import { Trend } from "k6/metrics";

const backendUrl = (__ENV.BACKEND_URL || "").replace(/\/$/, "");
const accessToken = __ENV.LINEAGEWEAVE_ACCESS_TOKEN || "";
const dashboardDuration = new Trend("lineageweave_operations_dashboard_duration", true);

export function setup() {
  if (!backendUrl || !accessToken) {
    fail("BACKEND_URL and LINEAGEWEAVE_ACCESS_TOKEN are required");
  }
}

export default function () {
  const response = http.get(`${backendUrl}/api/dashboard`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    tags: { endpoint: "operations_dashboard" },
  });
  dashboardDuration.add(response.timings.duration);
  check(response, {
    "authenticated Dashboard read succeeds": (value) => value.status === 200,
    "Dashboard retains a grounded case": (value) => {
      if (value.status !== 200) return false;
      const body = value.json();
      return Array.isArray(body.cases) && body.cases.length > 0;
    },
  });
}

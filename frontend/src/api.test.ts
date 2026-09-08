import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  askAgent,
  fetchMe,
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchOperationsDashboard,
  fetchRatingSourceOccupations,
  updateTenantConfig,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("backendFetch provider-error boundary", () => {
  it("binds the selected Dashboard period as inclusive API dates", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ cases: [] }), { headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchOperationsDashboard("access-token", "2026-08-01", "2026-08-25");

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/dashboard?period_start=2026-08-01&period_end=2026-08-25",
    );
  });

  it("encodes an exact occupation rating source request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ source_available: false, items: [] }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchOccupationRatings("access-token", {
      onetsocCode: "15-1252.00",
      dataReleaseCode: "onet-31.0",
      sourceTableCode: "abilities",
    });

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/occupations/15-1252.00/ratings?data_release_code=onet-31.0&source_table_code=abilities&limit=100&offset=0",
    );
  });

  it("reads the authenticated occupation source catalog", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ sources: [] }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchOccupationRatingSources("access-token");

    expect(fetchMock.mock.calls[0][0]).toContain("/api/occupation-rating-sources");
  });

  it("reads occupations for one exact imported source", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ occupations: [] }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchRatingSourceOccupations("access-token", "onet-31.0", "abilities");

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/occupation-rating-occupations?data_release_code=onet-31.0&source_table_code=abilities",
    );
  });

  it("does not expose provider details from server failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "provider secret and upstream stack trace" }),
          { status: 502, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 502,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it("turns transport failures into the same safe error type", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("provider secret")));

    await expect(fetchMe("access-token")).rejects.toBeInstanceOf(BackendError);
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 0,
      message: "The service is unreachable. Try again later.",
    });
  });

  it("keeps tenant settings on the shared error boundary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "provider diagnostic" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(updateTenantConfig("access-token", "Example tenant")).rejects.toMatchObject({
      status: 500,
      message: "The service could not complete this request. Try again later.",
    });
  });
});


describe("Ask polling cancellation", () => {
  it.each(["before submission", "during fetch"])("preserves cancellation %s", async (moment) => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockImplementation((_url: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(init.signal?.reason), { once: true });
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    if (moment === "before submission") controller.abort();
    const result = askAgent("token", "Question", false, undefined, controller.signal).catch((error: unknown) => error);
    if (moment === "during fetch") controller.abort();
    expect(await result).toBe(controller.signal.reason);
    expect(fetchMock).toHaveBeenCalledTimes(moment === "before submission" ? 0 : 1);
  });

  it("stops during the poll delay without another request", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ask_job_id: "job-1", job_status_code: "queued" }), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ job_status_code: "running" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ job_status_code: "succeeded", answer: {} })));
    vi.stubGlobal("fetch", fetchMock);
    const result = askAgent("token", "Question", false, undefined, controller.signal).catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    controller.abort();
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(await result).toBe(controller.signal.reason);
    expect(vi.getTimerCount()).toBe(0);
  });
});

it("keeps reading a live queued job after fifteen minutes", async () => {
  vi.useFakeTimers();
  const startedAt = Date.now();
  const answer = { answer: "Completed source-grounded answer", citations: [] };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ ask_job_id: "synthetic-job", job_status_code: "queued" }), { status: 202 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ job_status_code: "queued" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ job_status_code: "running" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ job_status_code: "succeeded", answer })));
  vi.stubGlobal("fetch", fetchMock);
  const result = askAgent("synthetic-token", "Synthetic question").catch((error: unknown) => error);
  await vi.advanceTimersByTimeAsync(0);
  vi.setSystemTime(startedAt + 16 * 60 * 1000);
  await vi.advanceTimersByTimeAsync(4000);
  expect(await result).toEqual(answer);
});


it.each([200, 503])("preserves custom cancellation reason while parsing a %i response body", async (status) => {
  const controller = new AbortController();
  const retirement = new Error("authorized screen retired");
  let rejectBody: (reason: unknown) => void = () => undefined;
  const body = new Promise<unknown>((_resolve, reject) => {
    rejectBody = reject;
  });
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockImplementation(() => body),
  } as unknown as Response);
  vi.stubGlobal("fetch", fetchMock);

  const result = askAgent("token", "Question", false, undefined, controller.signal).catch(
    (error: unknown) => error,
  );
  await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  controller.abort(retirement);
  rejectBody(new DOMException("The operation was aborted.", "AbortError"));

  expect(await result).toBe(retirement);
});

it.each([
  { job_status_code: "succeeded" },
  { job_status_code: "succeeded", answer: null },
  { job_status_code: "failed", failure_detail: "synthetic private diagnostic" },
  { job_status_code: "synthetic private diagnostic" },
  {},
  null,
])("stops observing a non-progress response without leaking its content: %j", async (job) => {
  vi.useFakeTimers();
  const controller = new AbortController();
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ ask_job_id: "synthetic-job", job_status_code: "queued" }), { status: 202 }))
    .mockImplementation(() => Promise.resolve(new Response(JSON.stringify(job))));
  vi.stubGlobal("fetch", fetchMock);
  let settled = false;
  const result = askAgent("synthetic-token", "Synthetic question", false, undefined, controller.signal)
    .catch((error: unknown) => error)
    .finally(() => { settled = true; });
  await vi.advanceTimersByTimeAsync(0);
  const settledBeforeCancellation = settled;
  const pendingTimers = vi.getTimerCount();
  controller.abort();

  expect(await result).toMatchObject({ message: "Ask Agent could not answer this question." });
  expect(settledBeforeCancellation).toBe(true);
  expect(pendingTimers).toBe(0);
  await vi.advanceTimersByTimeAsync(4000);
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

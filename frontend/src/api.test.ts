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
import { config } from "./config";

const defaultBackendBaseUrl = config.backendBaseUrl;

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  config.backendBaseUrl = defaultBackendBaseUrl;
});

describe("backendFetch provider-error boundary", () => {
  it("refuses a remote cleartext backend before attaching authorization", async () => {
    config.backendBaseUrl = "http://service.example";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchMe("access-token")).rejects.toMatchObject({ status: 0 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("bounds a stalled Ask submission by the whole-operation deadline", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
      ),
    );

    const pending = askAgent("access-token", "What changed?");
    const rejection = expect(pending).rejects.toThrow("timed out waiting for an answer");
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000);

    await rejection;
  });

  it("bounds a stalled Ask poll by the same whole-operation deadline", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ask_job_id: "job-1", job_status_code: "queued" })),
      )
      .mockImplementation((_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const pending = askAgent("access-token", "What changed?");
    const rejection = expect(pending).rejects.toThrow("timed out waiting for an answer");
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000);

    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("maps a stalled Ask response body to the whole-operation timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        Promise.resolve({
          ok: true,
          json: () =>
            new Promise((_resolve, reject) => {
              init?.signal?.addEventListener("abort", () =>
                reject(new DOMException("aborted", "AbortError")),
              );
            }),
        }),
      ),
    );

    const pending = askAgent("access-token", "What changed?");
    const rejection = expect(pending).rejects.toThrow("timed out waiting for an answer");
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000);

    await rejection;
  });
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

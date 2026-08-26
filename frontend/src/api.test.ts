import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  fetchMe,
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchOperationsDashboard,
  updateTenantConfig,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
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

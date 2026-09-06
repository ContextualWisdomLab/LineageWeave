import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  fetchMe,
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchOperationsDashboard,
  fetchRatingSourceOccupations,
  updateTenantConfig,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backendFetch provider-error boundary", () => {
  it.each([400, 401, 403, 404, 422])("keeps request identifiers out of an unreadable HTTP %s error", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not JSON", { status })));

    const error = await fetchOccupationRatings("synthetic-token", {
      onetsocCode: "synthetic-private-occupation",
      dataReleaseCode: "synthetic-private-release",
      sourceTableCode: "synthetic-private-source",
    }).catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(BackendError);
    expect(error).toMatchObject({
      status,
      message: "The service could not complete this request. Try again later.",
    });
    expect(String(error)).not.toContain("synthetic-private");
    expect(String(error)).not.toContain("/api/");
  });

  it("preserves actionable validation details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: "Choose an available source and try again." }),
      { status: 422 },
    )));
    await expect(fetchMe("synthetic-token")).rejects.toMatchObject({
      status: 422,
      message: "Choose an available source and try again.",
    });
  });

  it.each([200, 201])("hides malformed successful response bodies at HTTP %s", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(
      'synthetic-private-body {"unfinished":',
      { status, headers: { "Content-Type": "application/json" } },
    )));

    const error = await fetchMe("synthetic-token").catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(BackendError);
    expect(error).toMatchObject({
      status,
      message: "The service could not complete this request. Try again later.",
    });
    expect(String(error)).not.toContain("synthetic-private-body");
  });

  it("does not retry an unreadable successful write response", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(
      'synthetic-private-body {"unfinished":',
      { status: 201, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const error = await updateTenantConfig("synthetic-token", "Example tenant")
      .catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(BackendError);
    expect(error).toMatchObject({ status: 201, message: "The service could not complete this request. Try again later." });
    expect(String(error)).not.toContain("synthetic-private-body");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("hides body-stream failures after successful response headers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      new ReadableStream({
        start(controller) { controller.error(new Error("synthetic-private-stream")); },
      }),
      { status: 200 },
    )));
    await expect(fetchMe("synthetic-token")).rejects.toMatchObject({
      name: "BackendError",
      status: 200,
      message: "The service could not complete this request. Try again later.",
    });
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

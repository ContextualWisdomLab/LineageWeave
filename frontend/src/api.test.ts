import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  UserFacingError,
  askAgent,
  fetchMe,
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchOperationsDashboard,
  fetchPostLineage,
  fetchWorkerFunctionProfile,
  fetchRatingSourceOccupations,
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

  it("keeps special characters inside a post path segment", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ post_id: "post/with?reserved#characters" }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchPostLineage("access-token", "post/with?reserved#characters");

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/posts/post%2Fwith%3Freserved%23characters/lineage",
    );
  });

  it("keeps a worker-function domain inside one path segment", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ constructs: {}, relations: [] }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchWorkerFunctionProfile("access-token", "cognitive/unsafe", 1);

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/ontology/worker-functions/cognitive%2Funsafe/1",
    );
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

  it("normalizes malformed successful responses into a safe backend error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("not-json", { status: 200, headers: { "Content-Type": "application/json" } }),
      ),
    );

    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 502,
      message: "The service could not complete this request. Try again later.",
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

  it("surfaces a queued Ask job's bounded failure detail as a user-facing error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ ask_job_id: "ask-job-1", job_status_code: "queued" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              ask_job_id: "ask-job-1",
              job_status_code: "failed",
              failure_detail: "Ask Agent is unavailable: contextual-orchestrator returned no complete evidence object",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        ),
    );

    const failure = await askAgent("access-token", "Which project?").catch((caught: unknown) => caught);
    expect(failure).toBeInstanceOf(UserFacingError);
    expect((failure as UserFacingError).message).toBe(
      "Ask Agent is unavailable: contextual-orchestrator returned no complete evidence object",
    );
  });
});

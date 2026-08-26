import { afterEach, describe, expect, it, vi } from "vitest";
import { askAgent, BackendError, fetchMe, fetchOperationsDashboard, updateTenantConfig } from "./api";

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

describe("askAgent public-claim opt-in", () => {
  it("sends verify_external only when the reader opts in", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ask_job_id: "ask-job-1", job_status_code: "queued" }),
          { headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ask_job_id: "ask-job-1",
            job_status_code: "succeeded",
            answer: { answer_text: "synthetic", cited_post_ids: [], source_post_ids: [] },
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    await askAgent("access-token", "Does Northridge Grid exist?", true);

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({
      question: "Does Northridge Grid exist?",
      verify_external: true,
    });
  });

  it("defaults verify_external to false", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ask_job_id: "ask-job-1", job_status_code: "queued" }),
          { headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ask_job_id: "ask-job-1",
            job_status_code: "succeeded",
            answer: { answer_text: "synthetic", cited_post_ids: [], source_post_ids: [] },
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    await askAgent("access-token", "Which project?");

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({
      question: "Which project?",
      verify_external: false,
    });
  });
});

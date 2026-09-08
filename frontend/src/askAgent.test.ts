import { afterEach, describe, expect, it, vi } from "vitest";

import { askAgent } from "./api";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("Ask Agent job polling", () => {
  it("returns the stored answer after a queued poll without dropping request options", async () => {
    vi.useFakeTimers();
    const answer = {
      answer_text: "Recorded answer",
      cited_post_ids: [],
      source_post_ids: [],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-1", job_status_code: "queued" }))
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-1", job_status_code: "running" }))
      .mockResolvedValueOnce(
        jsonResponse({ ask_job_id: "ask-1", job_status_code: "succeeded", answer }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const pending = askAgent(
      "access-token",
      "What changed?",
      true,
      "2026-09-08T00:00:00+09:00",
    );
    await vi.runAllTimersAsync();

    await expect(pending).resolves.toEqual(answer);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({
        question: "What changed?",
        verify_external: true,
        knowledge_cutoff: "2026-09-08T00:00:00+09:00",
      }),
    });
    expect(fetchMock.mock.calls[1][0]).toContain("/api/ask/jobs/ask-1");
  });

  it("surfaces the recorded job failure detail", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-2", job_status_code: "queued" }))
      .mockResolvedValueOnce(
        jsonResponse({
          ask_job_id: "ask-2",
          job_status_code: "failed",
          failure_detail: "Evaluation evidence is unavailable.",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(askAgent("access-token", "Why?"))
      .rejects.toThrow("Evaluation evidence is unavailable.");
  });

  it("uses stable fallback guidance when a failed job has no detail", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-3", job_status_code: "queued" }))
      .mockResolvedValueOnce(
        jsonResponse({ ask_job_id: "ask-3", job_status_code: "failed", failure_detail: null }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(askAgent("access-token", "Why?"))
      .rejects.toThrow("Ask Agent could not answer this question.");
  });

  it("fails closed when a queued job is already beyond the client deadline", async () => {
    vi.spyOn(Date, "now")
      .mockReturnValueOnce(0)
      .mockReturnValue(15 * 60 * 1000 + 1);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-4", job_status_code: "queued" }))
      .mockResolvedValueOnce(jsonResponse({ ask_job_id: "ask-4", job_status_code: "running" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(askAgent("access-token", "Why?"))
      .rejects.toThrow("Ask Agent timed out waiting for an answer. Try again.");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

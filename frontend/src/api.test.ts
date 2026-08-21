import { afterEach, describe, expect, it, vi } from "vitest";
import { BackendError, fetchMe } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backendFetch provider-error boundary", () => {
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
});

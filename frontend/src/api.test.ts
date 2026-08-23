import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  fetchMe,
  fetchPosts,
  researchPostSources,
  setPostBookmark,
  updateTenantConfig,
} from "./api";

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

    await expect(updateTenantConfig("access-token", {
      brandName: "Example tenant",
      systemName: "Example system",
      copyrightYear: 2026,
      copyrightHolder: "Example tenant",
    })).rejects.toMatchObject({
      status: 500,
      message: "The service could not complete this request. Try again later.",
    });
  });
});

it("preserves list filters and explicit post mutations on the shared API boundary", async () => {
  const fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve(new Response("{}", { headers: { "Content-Type": "application/json" } })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await fetchPosts("access-token", 25, 50, "  project  ", ["voc"], ["parsed"], "private", "newest");
  await setPostBookmark("access-token", "post-1", true);
  await researchPostSources("access-token", "post-1");

  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "/api/posts?limit=25&offset=50&search=project&voc_type=voc&source_detail_state=parsed&visibility=private&sort=newest",
  );
  expect(fetchMock.mock.calls[1][1]).toMatchObject({
    method: "POST",
    body: JSON.stringify({ bookmarked: true }),
  });
  expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: "POST" });
});

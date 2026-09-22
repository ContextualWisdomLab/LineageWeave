import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendError,
  fetchMe,
  fetchWorkerFunctionProfile,
  fetchWorkerFunctionConstructCatalog,
  fetchPosts,
  fetchOntologyNeighborhood,
  setPostBookmark,
  fetchOccupationalConstructSearch,
  fetchProjectHistory,
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
  it.each(["{}", '{"detail":"   "}'])("keeps internal paths private when client guidance is absent: %s", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status: 403 })));
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      name: "BackendError", status: 403,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it.each(["invalid JSON", "interrupted body"])("sanitizes a successful HTTP response with %s", async (failure) => {
    const response = new Response("synthetic private upstream diagnostic", { status: 200 });
    if (failure === "interrupted body") {
      vi.spyOn(response, "json").mockRejectedValue(new Error("synthetic private body-read diagnostic"));
    }
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      name: "BackendError", status: 200,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it.each([401, 403, 409, 422])("retains actionable client-error details and HTTP status %s", async (status) => {
    const detail = "Select an available evidence source and retry.";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), { status }),
    ));
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      name: "BackendError", status, message: detail,
    });
  });

  it.each([
    ["profile", () => fetchWorkerFunctionProfile("access-token", "data", 0), "/api/ontology/worker-functions/data/0"],
    ["catalog", () => fetchWorkerFunctionConstructCatalog("access-token"), "/api/ontology/worker-function-constructs"],
  ] as const)("authenticates worker-function %s reads without fabricating unavailable evidence", async (_kind, read, endpoint) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(read()).rejects.toMatchObject({ name: "BackendError", status: 503 });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(endpoint), expect.objectContaining({
      headers: { Authorization: "Bearer access-token" },
    }));
  });

  it.each([false, true])("keeps post visibility and repeated Voice filters with legacy response %s", async (legacy) => {
    const page = { posts: [], total_count: 0, limit: 10, offset: 20 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(legacy ? [] : page)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchPosts("access-token", 10, 20, "  design & review  ", ["customer", "partner"], "public", "oldest")).resolves.toEqual(page);
    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/posts");
    expect([...url.searchParams]).toEqual([
      ["limit", "10"], ["offset", "20"], ["search", "design & review"],
      ["voc_type", "customer"], ["voc_type", "partner"], ["visibility", "public"], ["sort", "oldest"],
    ]);
    expect(options.headers.Authorization).toBe("Bearer access-token");
  });

  it.each([true, false])("authenticates bookmark selection %s without dropping false", async (bookmarked) => {
    const result = { bookmarked };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(result)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(setPostBookmark("access-token", "synthetic-post", bookmarked)).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/posts/synthetic-post/bookmark"), {
      method: "POST", body: JSON.stringify({ bookmarked }),
      headers: { Authorization: "Bearer access-token", "Content-Type": "application/json" },
    });
  });

  it("preserves ontology property repetition, cutoff, and opaque continuation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ nodes: [], edges: [] })));
    vi.stubGlobal("fetch", fetchMock);
    await fetchOntologyNeighborhood("access-token", {
      focusNodeType: "post", focusNodeId: "synthetic +/#", maximumDepth: 0,
      maximumNodes: 10, maximumEdges: 20, allowedPropertyCodes: ["wasDerivedFrom", "wasAttributedTo"],
      knowledgeCutoff: "2026-08-12T09:30:00+09:00", cursor: "opaque+/=&",
    });
    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/ontology/neighborhood");
    expect([...url.searchParams]).toEqual([
      ["focus_node_type", "post"], ["focus_node_id", "synthetic +/#"], ["maximum_depth", "0"],
      ["maximum_nodes", "10"], ["maximum_edges", "20"],
      ["knowledge_cutoff", "2026-08-12T09:30:00+09:00"], ["cursor", "opaque+/=&"],
      ["allowed_property_codes", "wasDerivedFrom"], ["allowed_property_codes", "wasAttributedTo"],
    ]);
    expect(options.headers.Authorization).toBe("Bearer access-token");
  });

  it.each([false, true])("preserves construct search filters and opaque continuation (%s)", async (withFilters) => {
    const response = { query: "Planning & analysis + 설계", family_code: null, hits: [], next_cursor: null };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
    vi.stubGlobal("fetch", fetchMock);
    const filters = withFilters ? {
      family: "worker_function", knowledgeCutoff: "2026-08-12T09:30:00+09:00",
      cursor: "https://synthetic.invalid/construct#A+B&next=1", limit: 0,
    } : {};
    await expect(fetchOccupationalConstructSearch("access-token", { query: response.query, ...filters })).resolves.toEqual(response);
    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/occupational-constructs/search");
    expect(Object.fromEntries(url.searchParams)).toEqual(withFilters ? {
      q: response.query, family: filters.family, knowledge_cutoff: filters.knowledgeCutoff,
      cursor: filters.cursor, limit: "0",
    } : { q: response.query });
    expect(options.headers.Authorization).toBe("Bearer access-token");
  });

  it.each([undefined, null, "2026-08-12T09:30:00+09:00"])("preserves project history identity and cutoff %s", async (cutoff) => {
    const response = { synthetic: true };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchProjectHistory("access-token", "Synthetic / A&B", "post +/?#", cutoff)).resolves.toEqual(response);
    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/projects/Synthetic%20%2F%20A%26B/history");
    expect(url.searchParams.get("focus_post_id")).toBe("post +/?#");
    expect(url.searchParams.get("knowledge_cutoff")).toBe(cutoff ?? null);
    expect([...url.searchParams.keys()]).toEqual(cutoff ? ["focus_post_id", "knowledge_cutoff"] : ["focus_post_id"]);
    expect(options.headers.Authorization).toBe("Bearer access-token");
  });

  it.each([
    "<html>upstream diagnostic</html>",
    "null",
    '"upstream diagnostic"',
    '{"error":"upstream diagnostic"}',
    '{"detail":{"error":"upstream diagnostic"}}',
  ])("keeps malformed server error payloads private: %s", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status: 503 })));
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      name: "BackendError",
      status: 503,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it("authenticates tenant mutations and sends an exact JSON body", async () => {
    const result = { brandName: "Synthetic tenant" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(result)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(updateTenantConfig("access-token", result.brandName)).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/settings"), {
      method: "PATCH",
      body: JSON.stringify(result),
      headers: { Authorization: "Bearer access-token", "Content-Type": "application/json" },
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

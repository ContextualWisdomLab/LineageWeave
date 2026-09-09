import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchLineageGraph, fetchPosts } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("read-model collection defaults", () => {
  it("keeps the unfiltered legacy posts collection query-free and derives paging defaults", async () => {
    const legacyPosts = [{ post_id: "synthetic-post" }];
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(legacyPosts)));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchPosts("access-token")).resolves.toEqual({
      posts: legacyPosts,
      total_count: 1,
      limit: 1,
      offset: 0,
    });

    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/posts");
    expect(url.search).toBe("");
    expect(options.headers.Authorization).toBe("Bearer access-token");
  });

  it("starts an explicitly paged posts collection at offset zero", async () => {
    const page = { posts: [], total_count: 0, limit: 10, offset: 0 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(page)));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchPosts("access-token", 10)).resolves.toEqual(page);

    const [request] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect([...url.searchParams]).toEqual([
      ["limit", "10"],
      ["offset", "0"],
    ]);
  });

  it("loads the whole lineage graph without fabricating a focused post query", async () => {
    const graph = { nodes: [], edges: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(graph)));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchLineageGraph("access-token")).resolves.toEqual(graph);

    const [request] = fetchMock.mock.calls[0];
    const url = new URL(request, "https://synthetic.invalid");
    expect(url.pathname).toBe("/api/lineage");
    expect(url.search).toBe("");
  });
});

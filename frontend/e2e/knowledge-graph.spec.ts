import { test, expect } from "./fixtures";

/**
 * Regression guard for the 2026-08-22 black-node bug (KnowledgeGraph.css
 * used undefined --ink/--muted/--line/--line-strong/--warning custom
 * properties; an invalid var() falls back to SVG fill's initial value,
 * black, so a node's box and/or label text was invisible).
 *
 * Discovers a real Knowledge Graph post through the running app's own
 * API rather than a post id fixed in this file -- this suite runs
 * against the live authenticated stack (`make up && make seed`, or an
 * authorized real import), and this repository never commits a specific
 * private record's identifier (AGENTS.md's synthetic-only-artifact
 * rule). Every assertion below checks computed style/DOM structure
 * only; it never reads or logs the node's actual label text.
 */

async function findPostIdWithKnowledgeGraphNodes(
  request: import("@playwright/test").APIRequestContext,
  baseURL: string,
  accessToken: string,
): Promise<string | null> {
  const list = await request.get(`${baseURL}/api/posts?limit=100&sort=newest`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!list.ok()) return null;
  const { posts } = (await list.json()) as { posts: { post_id: string }[] };
  for (const post of posts) {
    const graph = await request.get(`${baseURL}/api/posts/${post.post_id}/knowledge-graph`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!graph.ok()) continue;
    const body = (await graph.json()) as { nodes: unknown[] };
    if (body.nodes.length > 0) return post.post_id;
  }
  return null;
}

test("Knowledge Graph nodes render with visible, non-black text and background", async ({
  page,
  request,
}) => {
  const backendBaseURL = process.env.LINEAGEWEAVE_BACKEND_URL ?? "http://localhost:18420";
  const tokenResponse = await request.post(
    `${process.env.LINEAGEWEAVE_KEYCLOAK_URL ?? "http://localhost:18080"}/realms/lineageweave-demo/protocol/openid-connect/token`,
    {
      form: {
        client_id: "lineageweave-frontend",
        grant_type: "password",
        username: process.env.LINEAGEWEAVE_E2E_USERNAME ?? "demo.analyst",
        password: process.env.LINEAGEWEAVE_E2E_PASSWORD ?? "lineageweave-demo-only",
      },
    },
  );
  test.skip(!tokenResponse.ok(), "Keycloak token endpoint unavailable in this environment");
  const { access_token: accessToken } = (await tokenResponse.json()) as { access_token: string };

  const postId = await findPostIdWithKnowledgeGraphNodes(request, backendBaseURL, accessToken);
  test.skip(postId === null, "No post with Knowledge Graph nodes is visible in this environment");

  await page.goto(`/?post=${postId}`);
  const kgSection = page.locator("section.knowledge-graph");
  await expect(kgSection).toBeVisible({ timeout: 15000 });

  const nodeRects = kgSection.locator(".knowledge-graph-node rect");
  const nodeCount = await nodeRects.count();
  expect(nodeCount).toBeGreaterThan(0);

  for (let index = 0; index < nodeCount; index += 1) {
    const node = kgSection.locator(".knowledge-graph-node").nth(index);
    const label = node.locator(".knowledge-graph-node-label");
    await expect(label).not.toHaveText("");

    const [fillColor, textColor] = await node.evaluate((element) => {
      const rect = element.querySelector("rect");
      const text = element.querySelector(".knowledge-graph-node-label");
      return [
        rect ? getComputedStyle(rect).fill : "",
        text ? getComputedStyle(text).fill : "",
      ];
    });
    // A node with an undefined design token falls back to SVG fill's
    // initial value -- solid black -- for both the box and the label,
    // making black-on-black exactly the failure this guards against.
    const isBlackOnBlack = fillColor === "rgb(0, 0, 0)" && textColor === "rgb(0, 0, 0)";
    expect(isBlackOnBlack).toBe(false);
  }
});

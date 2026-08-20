import { afterEach, describe, expect, it, vi } from "vitest";
import { askAgent } from "./api";

describe("Global Ask public verification contract", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends explicit verification consent and keeps web evidence separate", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          answer_text: "Apollo is described by the cited post.",
          cited_post_ids: ["post-1"],
          cited_posts: [{ post_id: "post-1", post_title: "Apollo" }],
          cited_post_evidence: [],
          source_post_ids: ["post-1"],
          external_verification_status: "external_verification_completed",
          external_claims: [
            {
              claim_text: "project: Apollo",
              claim_kind: "semantic_project",
              status_code: "claim_supported",
              rationale: "A public source corroborates the claim.",
              source_post_ids: ["post-1"],
              evidence: [
                {
                  title: "Public evidence",
                  url: "https://example.com/apollo",
                  snippet: "Apollo is a project.",
                },
              ],
            },
          ],
          next_action: "Open the cited public evidence and review the internal claim.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await askAgent("access-token", "Apollo", true);

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      question: "Apollo",
      verify_external: true,
    });
    expect(response.external_verification_status).toBe(
      "external_verification_completed",
    );
    expect(response.external_claims[0].evidence[0].url).toBe(
      "https://example.com/apollo",
    );
    expect(response.cited_post_ids).toEqual(["post-1"]);
  });
});

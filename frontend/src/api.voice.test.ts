import { afterEach, describe, expect, it, vi } from "vitest";
import { createPostVoiceAssignment } from "./api";

describe("createPostVoiceAssignment", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the open authorized post as explicit evidence", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: "vops",
      label: "Voice of Process",
      is_primary: false,
      truth_status_code: "truth_observed",
      evidence_available: true,
    }), { status: 201, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await createPostVoiceAssignment("token", "post-1", "vops", "truth_observed");

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/posts/post-1/voice-assignments");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      voice_type_code: "vops",
      truth_status_code: "truth_observed",
      evidence_post_id: "post-1",
    });
  });
});

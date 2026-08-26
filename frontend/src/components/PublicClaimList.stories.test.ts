import { describe, expect, it } from "vitest";
import meta, { Empty, UnavailableSearch } from "./PublicClaimList.stories";

describe("PublicClaimList Storybook contract", () => {
  it("exports CSF metadata for the public-claim evidence states", () => {
    expect(meta.title).toBe("Evidence/PublicClaimList");
    expect(meta.component).toBeDefined();
    expect(meta.args.claims[0].status_code).toBe("claim_supported");
    expect(UnavailableSearch.args?.claims?.[0]?.external_evidence_urls).toEqual([]);
    expect(Empty.args?.claims).toEqual([]);
  });
});

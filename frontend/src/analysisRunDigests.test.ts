import { describe, expect, it } from "vitest";
import {
  ANALYSIS_RUN_DIGEST_PREFIX_LENGTH,
  analysisRunDigestButtonLabel,
  analysisRunDigestKindLabel,
  analysisRunDigestNextAction,
  analysisRunDigestPrefix,
} from "./analysisRunDigests";

const CODE_REVISION_SHA = "abcdef0123456789deadbeefcafebabe";
const CONFIGURATION_SHA256 =
  "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

describe("analysisRunDigestPrefix", () => {
  it("keeps a 12-character prefix so the operator can match git-style short SHAs", () => {
    expect(ANALYSIS_RUN_DIGEST_PREFIX_LENGTH).toBe(12);
    expect(analysisRunDigestPrefix(CODE_REVISION_SHA)).toBe("abcdef012345");
    expect(analysisRunDigestPrefix(CONFIGURATION_SHA256)).toBe("0123456789ab");
  });

  it("returns the whole digest when it is shorter than the prefix length", () => {
    expect(analysisRunDigestPrefix("abc")).toBe("abc");
  });
});

describe("analysisRunDigestKindLabel", () => {
  it("names the two registered digest kinds without inventing a third", () => {
    expect(analysisRunDigestKindLabel("code")).toBe("Code");
    expect(analysisRunDigestKindLabel("config")).toBe("Config");
  });
});

describe("analysisRunDigestButtonLabel", () => {
  it("puts the kind and prefix in the accessible name, not the full digest", () => {
    expect(analysisRunDigestButtonLabel("code", CODE_REVISION_SHA)).toBe(
      "Code abcdef012345",
    );
    expect(analysisRunDigestButtonLabel("config", CONFIGURATION_SHA256)).toBe(
      "Config 0123456789ab",
    );
    expect(analysisRunDigestButtonLabel("code", CODE_REVISION_SHA)).not.toContain(
      CODE_REVISION_SHA,
    );
  });
});

describe("analysisRunDigestNextAction", () => {
  it("tells every operator to activate a prefix, not to hover", () => {
    const nextAction = analysisRunDigestNextAction();
    expect(nextAction).toMatch(/Activate a prefix/);
    expect(nextAction).not.toMatch(/Hover/i);
  });
});

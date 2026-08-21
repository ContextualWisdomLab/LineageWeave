import { describe, expect, it } from "vitest";
import { decodeHtmlEntities } from "./postBodyDisplay";

describe("decodeHtmlEntities", () => {
  it("turns source HTML entities into safe display text", () => {
    expect(decodeHtmlEntities("1. 회사소개 &nbsp; 2. 특허기술 &amp; 적용"))
      .toBe("1. 회사소개   2. 특허기술 & 적용");
  });
});

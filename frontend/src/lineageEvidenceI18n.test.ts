import { describe, expect, it } from "vitest";
import { SUPPORTED_LOCALES } from "./i18n";
import {
  LINEAGE_EVIDENCE_KEYS,
  lineageEvidenceText,
} from "./lineageEvidenceI18n";

describe("lineage evidence copy", () => {
  it("defines every Buyer audit label for every supported locale", () => {
    for (const locale of SUPPORTED_LOCALES) {
      for (const key of LINEAGE_EVIDENCE_KEYS) {
        expect(lineageEvidenceText(key, locale).trim()).not.toBe("");
      }
    }
  });

  it("gives Korean buyers localized evidence, provenance, and non-causal guidance", () => {
    expect(lineageEvidenceText("whyLinked", "ko")).toBe(
      "이 게시물이 연결된 이유",
    );
    expect(lineageEvidenceText("nextAction", "ko")).toBe(
      "이 연결을 신뢰하기 전에 채널별 정확한 점수를 검토하세요.",
    );
    expect(lineageEvidenceText("weight", "ko")).toBe("가중치");
    expect(lineageEvidenceText("contribution", "ko")).toBe("기여도");
    expect(lineageEvidenceText("inferredNotice", "ko")).toBe(
      "이 연결은 추론된 근거이며 인과적 사실이 아닙니다.",
    );
    expect(lineageEvidenceText("llmNotUsed", "ko")).toBe(
      "이 연결에는 LLM 판정이 사용되지 않았습니다.",
    );
    expect(lineageEvidenceText("notAvailable", "ko")).toBe("사용할 수 없음");
  });

  it("keeps the evidence concepts consistent across non-English locales", () => {
    expect(lineageEvidenceText("secondaryKey", "zh")).toBe("次级键匹配");
    expect(lineageEvidenceText("contribution", "ja")).toBe("寄与度");
    expect(lineageEvidenceText("llm", "vi")).toBe("Phán định LLM");
  });
});

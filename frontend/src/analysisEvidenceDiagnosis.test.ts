import { describe, expect, it } from "vitest";
import {
  analysisEvidenceDiagnosis,
  gluedRoleRelationshipNextAction,
} from "./analysisEvidenceDiagnosis";

describe("analysisEvidenceDiagnosis", () => {
  it("keeps catalog-unbound, dropped-channel, and confident-negative distinguishable", () => {
    const unbound = analysisEvidenceDiagnosis("catalog_unbound");
    const dropped = analysisEvidenceDiagnosis("dropped_channel");
    const negative = analysisEvidenceDiagnosis("confident_negative");

    expect(unbound.title).not.toBe(dropped.title);
    expect(unbound.title).not.toBe(negative.title);
    expect(dropped.title).not.toBe(negative.title);
    expect(unbound.nextAction).not.toBe(dropped.nextAction);
    expect(unbound.nextAction).not.toBe(negative.nextAction);
    expect(dropped.nextAction).not.toBe(negative.nextAction);

    expect(unbound.nextAction.toLowerCase()).toMatch(/unbound/);
    expect(unbound.nextAction.toLowerCase()).toMatch(/not a missing analysis channel/);
    expect(unbound.nextAction.toLowerCase()).not.toMatch(/retry when the channel/);
    expect(dropped.nextAction.toLowerCase()).toMatch(/missing signal is not a negative fact/);
    expect(dropped.nextAction.toLowerCase()).not.toMatch(/catalog/);
    expect(negative.nextAction.toLowerCase()).toMatch(/measured negative/);
    expect(negative.nextAction.toLowerCase()).not.toMatch(/unbound|retry when the channel/);
  });

  it("fail-closes a glued source phrase instead of inventing an operates relation", () => {
    const copy = gluedRoleRelationshipNextAction();
    expect(copy.toLowerCase()).toMatch(/source phrase/);
    expect(copy.toLowerCase()).toMatch(/job title and relationship type/);
    expect(copy.toLowerCase()).not.toMatch(/operates/);
  });

  it("fails closed when an untyped caller supplies an unknown diagnosis", () => {
    expect(() =>
      analysisEvidenceDiagnosis("unknown" as never),
    ).toThrow("Unsupported analysis evidence diagnosis: unknown");
  });
});

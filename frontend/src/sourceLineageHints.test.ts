import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "./i18n";
import { sourceLineageContextLabel, sourceLineageFieldLabel } from "./sourceLineageHints";

afterEach(() => {
  setLocale("en");
});

describe("source lineage hint labels", () => {
  it("localizes a known commercial context and its fields", () => {
    setLocale("ko");

    expect(
      sourceLineageContextLabel({
        combination_code: "1100",
        commercial_context_code: "customer_order_pool_candidate",
        inference_status_code: "inferred",
        present_fields: ["customer", "order_pool"],
        missing_fields: ["sales_order", "sales_order_item"],
        lifecycle_vector: "STAGE/D/IP/N",
        deleted_marker_present: true,
      }),
    ).toBe("고객 + 오더 풀 후보");
    expect(sourceLineageFieldLabel("customer")).toBe("고객 코드");
    expect(sourceLineageFieldLabel("unknown_field")).toBe("unknown_field");
  });

  it("falls back to the source code for unknown contexts", () => {
    expect(
      sourceLineageContextLabel({
        combination_code: "0000",
        commercial_context_code: "unregistered_context",
        inference_status_code: "inferred",
        present_fields: [],
        missing_fields: ["customer"],
        lifecycle_vector: "none/none/none/none",
        deleted_marker_present: false,
      }),
    ).toBe("unregistered_context");
  });
});

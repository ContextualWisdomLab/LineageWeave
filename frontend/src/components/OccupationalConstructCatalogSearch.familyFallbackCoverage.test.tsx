import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { setLocale } from "../i18n";
import { OccupationalConstructCatalogSearch } from "./OccupationalConstructCatalogSearch";

describe("OccupationalConstructCatalogSearch family fallback", () => {
  afterEach(() => setLocale("en"));

  it("keeps an unknown persisted family visible under the generic work-evidence label", () => {
    setLocale("en");
    render(
      <OccupationalConstructCatalogSearch
        page={{
          query: "Oral",
          family_code: null,
          next_cursor: null,
          hits: [
            {
              construct_id: "99999999-9999-9999-9999-999999999999",
              construct_iri: "https://example.invalid/construct/future-family",
              construct_family_code: "future_family",
              preferred_label: "Oral Comprehension",
              vocabulary_version: "future",
              supporting_post_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
              supporting_post_title: "Supporting record",
              evidence_text: "reviewed the written procedure",
              truth_status_code: "truth_inferred",
            },
          ],
        }}
        status="ready"
      />,
    );

    expect(screen.getByText("Work evidence")).toBeVisible();
    expect(
      screen.getByRole("button", {
        name: "Open supporting record: Oral Comprehension · Supporting record",
      }),
    ).toBeVisible();
  });
});

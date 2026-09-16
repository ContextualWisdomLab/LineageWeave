import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { OccupationalConstructAssertion } from "../api";
import { setLocale } from "../i18n";
import { OccupationalConstructEvidence } from "./OccupationalConstructEvidence";

const UNKNOWN_FAMILY_ASSERTION: OccupationalConstructAssertion = {
  construct_iri: "https://example.invalid/work-evidence/future-family",
  construct_family_code: "future_family",
  preferred_label: "Future construct",
  vocabulary_iri: "https://example.invalid/work-evidence",
  vocabulary_version: "future",
  evidence_text: "reviewed the persisted source record",
  truth_status_code: "truth_inferred",
  extraction_method: "released_owner_contract",
  generated_at: "2026-09-09T00:00:00Z",
  unit_index: 0,
  provenance: "post_occupational_construct_assertion.evidence_text",
};

afterEach(() => setLocale("en"));

it("keeps an unknown persisted construct family visible with the generic work-evidence label", () => {
  render(
    <OccupationalConstructEvidence status="complete" assertions={[UNKNOWN_FAMILY_ASSERTION]} />,
  );

  const evidenceItem = screen.getByRole("listitem");
  expect(within(evidenceItem).getByText("Future construct")).toBeVisible();
  expect(within(evidenceItem).getByText("Work evidence")).toBeVisible();
  expect(within(evidenceItem).getByText("reviewed the persisted source record")).toBeVisible();
});

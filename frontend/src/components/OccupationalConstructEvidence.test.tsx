import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "../i18n";
import type { OccupationalConstructAssertion } from "../api";
import { OccupationalConstructEvidence } from "./OccupationalConstructEvidence";

const ASSERTION: OccupationalConstructAssertion = {
  construct_iri: "https://data.onetcenter.org/element/1.A.1.a.1",
  construct_family_code: "cognitive_ability",
  preferred_label: "Oral Comprehension",
  vocabulary_iri: "https://www.onetcenter.org/database.html",
  vocabulary_version: "31.0",
  evidence_text: "reviewed the written procedure",
  truth_status_code: "truth_inferred",
  extraction_method: "contextual_orchestrator_onet_hierarchy_v1",
  generated_at: "2026-08-27T00:00:00Z",
  unit_index: 1,
  provenance: "post_occupational_construct_assertion.evidence_text",
};

describe("OccupationalConstructEvidence", () => {
  afterEach(() => setLocale("en"));

  it("shows the exact evidence, inference status, and official definition action", async () => {
    render(<OccupationalConstructEvidence status="complete" assertions={[ASSERTION]} />);
    expect(screen.getByRole("heading", { name: "Work evidence" })).toBeVisible();
    expect(screen.getByText("reviewed the written procedure")).toBeVisible();
    await userEvent.click(screen.getByText("Evidence details"));
    expect(screen.getByRole("img", { name: /Inference:/ })).toBeVisible();
    expect(screen.getByRole("link", { name: "Open catalog definition" })).toHaveAttribute(
      "href",
      ASSERTION.construct_iri,
    );
    expect(screen.queryByText(ASSERTION.extraction_method)).not.toBeInTheDocument();
  });

  it.each([
    ["complete", [], "No supported work evidence was found in this record."],
    ["processing", [], "Work evidence is still being prepared. Reopen this record shortly."],
    ["unavailable", [], "Work evidence is unavailable. Ask an administrator to retry record analysis."],
    [
      "historical_unavailable",
      [],
      "Work evidence is unavailable for this historical cutoff. Review the known body instead.",
    ],
  ] as const)("renders the %s state without invented evidence", (status, assertions, message) => {
    render(<OccupationalConstructEvidence status={status} assertions={[...assertions]} />);
    expect(screen.getByRole("status")).toHaveTextContent(message);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("localizes the next action", () => {
    setLocale("ko");
    render(<OccupationalConstructEvidence status="unavailable" assertions={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent("관리자에게 기록 분석 재시도를 요청하세요");
  });
});

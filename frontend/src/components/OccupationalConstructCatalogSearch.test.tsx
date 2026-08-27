import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BackendError, fetchOccupationalConstructSearch } from "../api";
import { setLocale } from "../i18n";
import { OccupationalConstructCatalogSearch } from "./OccupationalConstructCatalogSearch";

vi.mock("../api", async (importActual) => {
  const actual = await importActual<typeof import("../api")>();
  return { ...actual, fetchOccupationalConstructSearch: vi.fn() };
});

const HIT = {
  construct_id: "99999999-9999-9999-9999-999999999999",
  construct_iri: "https://data.onetcenter.org/element/1.A.1.a.1",
  construct_family_code: "cognitive_ability",
  preferred_label: "Oral Comprehension",
  vocabulary_version: "31.0",
  supporting_post_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
  supporting_post_title: "Synthetic briefing",
  evidence_text: "reviewed the written procedure",
  truth_status_code: "truth_inferred",
};

describe("OccupationalConstructCatalogSearch", () => {
  afterEach(() => {
    setLocale("en");
    vi.mocked(fetchOccupationalConstructSearch).mockReset();
  });

  it("does not search until two letters are submitted", async () => {
    const user = userEvent.setup();
    render(<OccupationalConstructCatalogSearch accessToken="token" />);
    await user.type(screen.getByLabelText("Catalog label"), "O");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    expect(fetchOccupationalConstructSearch).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Type two or more letters of a catalog label, then open the supporting record.",
    );
  });

  it("opens the supporting record from a visible catalog match", async () => {
    const user = userEvent.setup();
    const onSelectPost = vi.fn();
    vi.mocked(fetchOccupationalConstructSearch).mockResolvedValue({
      query: "Oral",
      family_code: null,
      next_cursor: null,
      hits: [HIT],
    });
    render(
      <OccupationalConstructCatalogSearch accessToken="token" onSelectPost={onSelectPost} />,
    );
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.selectOptions(screen.getByLabelText("Work-evidence family"), "cognitive_ability");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    expect(fetchOccupationalConstructSearch).toHaveBeenCalledWith("token", {
      query: "Oral",
      family: "cognitive_ability",
      knowledgeCutoff: undefined,
    });
    await user.click(
      screen.getByRole("button", { name: "Open supporting record: Oral Comprehension · Synthetic briefing" }),
    );
    expect(onSelectPost).toHaveBeenCalledWith(HIT.supporting_post_id);
    expect(screen.getByText("Open the supporting record")).toBeVisible();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
  });

  it("keeps empty and error states honest", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchOccupationalConstructSearch).mockResolvedValueOnce({
      query: "Oral",
      family_code: null,
      next_cursor: null,
      hits: [],
    });
    const { rerender } = render(<OccupationalConstructCatalogSearch accessToken="token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "No visible work evidence matches. Open a record with work evidence next.",
    );

    vi.mocked(fetchOccupationalConstructSearch).mockRejectedValueOnce(
      new BackendError("/api/occupational-constructs/search", 500),
    );
    rerender(<OccupationalConstructCatalogSearch accessToken="token" />);
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Work-evidence search is unavailable. Open a visible record next.",
    );
  });

  it("localizes the next action", () => {
    setLocale("ko");
    render(
      <OccupationalConstructCatalogSearch
        page={{ query: "Oral", family_code: null, next_cursor: null, hits: [HIT] }}
        status="ready"
      />,
    );
    expect(screen.getByText("뒷받침하는 기록 열기")).toBeVisible();
  });
});

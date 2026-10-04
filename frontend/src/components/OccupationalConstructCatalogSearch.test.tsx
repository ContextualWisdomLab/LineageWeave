import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BackendError, fetchOccupationalConstructSearch } from "../api";
import type { OccupationalConstructSearchPage } from "../api";
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

  it("continues from next_cursor and retains earlier matches", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchOccupationalConstructSearch)
      .mockResolvedValueOnce({
        query: "Oral",
        family_code: null,
        next_cursor: HIT.construct_iri,
        hits: [HIT],
      })
      .mockResolvedValueOnce({
        query: "Oral",
        family_code: null,
        next_cursor: null,
        hits: [{ ...HIT, construct_id: "second", preferred_label: "Written Comprehension" }],
      });
    render(<OccupationalConstructCatalogSearch accessToken="token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await user.click(screen.getByRole("button", { name: "Show more matching records" }));
    expect(fetchOccupationalConstructSearch).toHaveBeenLastCalledWith("token", {
      query: "Oral",
      family: undefined,
      knowledgeCutoff: undefined,
      cursor: HIT.construct_iri,
    });
    expect(screen.getByText(/Oral Comprehension/)).toBeVisible();
    expect(screen.getByText(/Written Comprehension/)).toBeVisible();
  });

  it.each(["success", "denial"])("ignores an earlier search's late %s", async (completion) => {
    const user = userEvent.setup();
    let resolve!: (page: OccupationalConstructSearchPage) => void;
    let reject!: (error: BackendError) => void;
    vi.mocked(fetchOccupationalConstructSearch)
      .mockImplementationOnce(() => new Promise((yes, no) => { resolve = yes; reject = no; }))
      .mockResolvedValueOnce({ query: "Written", family_code: null, next_cursor: null, hits: [
        { ...HIT, preferred_label: "Written Comprehension" },
      ] });
    render(<OccupationalConstructCatalogSearch accessToken="synthetic-token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await user.clear(screen.getByLabelText("Catalog label"));
    await user.type(screen.getByLabelText("Catalog label"), "Written");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await act(async () => {
      if (completion === "success") resolve({ query: "Oral", family_code: null, next_cursor: null, hits: [HIT] });
      else reject(new BackendError("/api/occupational-constructs/search", 403));
    });
    expect(screen.getByRole("button", { name: /Open supporting record: Written Comprehension/ })).toBeVisible();
    expect(screen.queryByRole("button", { name: /Open supporting record: Oral Comprehension/ })).not.toBeInTheDocument();
  });

  it.each(["success", "denial"])("ignores an old continuation's late %s after a newer search", async (completion) => {
    const user = userEvent.setup();
    let resolve!: (page: OccupationalConstructSearchPage) => void;
    let reject!: (error: BackendError) => void;
    vi.mocked(fetchOccupationalConstructSearch)
      .mockResolvedValueOnce({ query: "Oral", family_code: null, next_cursor: HIT.construct_iri, hits: [HIT] })
      .mockImplementationOnce(() => new Promise((yes, no) => { resolve = yes; reject = no; }))
      .mockResolvedValueOnce({ query: "Written", family_code: null, next_cursor: null, hits: [
        { ...HIT, preferred_label: "Written Comprehension" },
      ] });
    render(<OccupationalConstructCatalogSearch accessToken="synthetic-token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await user.click(screen.getByRole("button", { name: "Show more matching records" }));
    await user.clear(screen.getByLabelText("Catalog label"));
    await user.type(screen.getByLabelText("Catalog label"), "Written");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await act(async () => {
      if (completion === "success") resolve({ query: "Oral", family_code: null, next_cursor: null, hits: [
        { ...HIT, construct_id: "second", preferred_label: "Old continuation" },
      ] });
      else reject(new BackendError("/api/occupational-constructs/search", 403));
    });
    expect(screen.getByRole("button", { name: /Open supporting record: Written Comprehension/ })).toBeVisible();
    expect(screen.queryByRole("button", { name: /Open supporting record: Old continuation/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open supporting record: Oral Comprehension/ })).not.toBeInTheDocument();
  });

  it.each([
    { accessToken: "another-synthetic-token", knowledgeCutoff: undefined },
    { accessToken: undefined, knowledgeCutoff: undefined },
    { accessToken: "synthetic-token", knowledgeCutoff: "2026-01-01T00:00:00Z" },
  ])("clears evidence and rejects pending results when reader scope changes: %j", async (scope) => {
    const user = userEvent.setup();
    let resolve!: (page: OccupationalConstructSearchPage) => void;
    vi.mocked(fetchOccupationalConstructSearch)
      .mockResolvedValueOnce({ query: "Oral", family_code: null, next_cursor: HIT.construct_iri, hits: [HIT] })
      .mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    const { rerender } = render(<OccupationalConstructCatalogSearch accessToken="synthetic-token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await user.click(screen.getByRole("button", { name: "Show more matching records" }));
    rerender(<OccupationalConstructCatalogSearch {...scope} />);
    await act(async () => resolve({ query: "Oral", family_code: null, next_cursor: null, hits: [{ ...HIT, construct_id: "second", preferred_label: "Old continuation" }] }));
    expect(screen.queryByRole("button", { name: /Open supporting record: Oral Comprehension/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open supporting record/ })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Type two or more letters");
  });

  it.each([
    { accessToken: "another-synthetic-token", knowledgeCutoff: undefined },
    { accessToken: undefined, knowledgeCutoff: undefined },
    { accessToken: "synthetic-token", knowledgeCutoff: "2026-01-01T00:00:00Z" },
  ])("clears displayed evidence on reader-scope change: %j", (scope) => {
    const { rerender } = render(<OccupationalConstructCatalogSearch
      accessToken="synthetic-token"
      page={{ query: "Oral", family_code: null, next_cursor: HIT.construct_iri, hits: [HIT] }}
    />);
    expect(screen.getByRole("button", { name: /Open supporting record: Oral Comprehension/ })).toBeVisible();
    rerender(<OccupationalConstructCatalogSearch {...scope} />);
    expect(screen.queryByRole("button", { name: /Open supporting record/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more matching records" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Catalog label")).toHaveValue("");
  });

  it("invalidates a pending search when a short query is submitted", async () => {
    const user = userEvent.setup();
    let resolve!: (page: OccupationalConstructSearchPage) => void;
    vi.mocked(fetchOccupationalConstructSearch).mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    render(<OccupationalConstructCatalogSearch accessToken="synthetic-token" />);
    await user.type(screen.getByLabelText("Catalog label"), "Oral");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await user.clear(screen.getByLabelText("Catalog label"));
    await user.type(screen.getByLabelText("Catalog label"), "O");
    await user.click(screen.getByRole("button", { name: "Find matching records" }));
    await act(async () => resolve({ query: "Oral", family_code: null, next_cursor: null, hits: [HIT] }));
    expect(screen.queryByRole("button", { name: /Open supporting record/ })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Type two or more letters");
    expect(fetchOccupationalConstructSearch).toHaveBeenCalledTimes(1);
  });
});

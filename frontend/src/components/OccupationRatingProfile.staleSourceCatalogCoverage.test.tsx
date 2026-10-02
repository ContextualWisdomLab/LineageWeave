import { act, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import {
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchRatingSourceOccupations,
} from "../api";
import { OccupationRatingProfile } from "./OccupationRatingProfile";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOccupationRatingSources: vi.fn(),
  fetchOccupationRatings: vi.fn(),
  fetchRatingSourceOccupations: vi.fn(),
}));

const replacementSource = {
  data_release_code: "onet-31.0",
  release_version: "31.0",
  source_publisher_name: "Synthetic publisher",
  source_license_url: "https://example.test/license",
  source_table_code: "work_styles",
  source_table_name: "Work Styles",
  source_artifact_url: "https://example.test/work-styles.csv",
  source_artifact_sha256: "b".repeat(64),
  source_row_count: 2,
};

const supersededSource = {
  data_release_code: "onet-30.0",
  release_version: "30.0",
  source_publisher_name: "Synthetic publisher",
  source_license_url: "https://example.test/license",
  source_table_code: "abilities",
  source_table_name: "Abilities",
  source_artifact_url: "https://example.test/abilities.csv",
  source_artifact_sha256: "a".repeat(64),
  source_row_count: 2,
};

beforeEach(() => {
  vi.mocked(fetchOccupationRatingSources).mockReset();
  vi.mocked(fetchOccupationRatings).mockReset();
  vi.mocked(fetchRatingSourceOccupations).mockReset();
});

it("ignores a successful source catalog from a superseded access token", async () => {
  let resolveSuperseded: ((value: { sources: typeof supersededSource[] }) => void) | undefined;
  vi.mocked(fetchOccupationRatingSources)
    .mockImplementationOnce(() => new Promise((resolve) => { resolveSuperseded = resolve; }))
    .mockResolvedValueOnce({ sources: [replacementSource] });
  vi.mocked(fetchRatingSourceOccupations).mockResolvedValue({
    data_release_code: "onet-31.0",
    source_table_code: "work_styles",
    source_available: true,
    occupations: [
      { onetsoc_code: "15-1252.00", occupation_title: "Software Developers" },
    ],
  });

  const { rerender } = render(<OccupationRatingProfile accessToken="token-old" />);
  rerender(<OccupationRatingProfile accessToken="token-new" />);

  expect(await screen.findByRole("option", { name: "31.0 · Work Styles" })).toBeInTheDocument();
  expect(fetchRatingSourceOccupations).toHaveBeenCalledWith(
    "token-new",
    "onet-31.0",
    "work_styles",
  );

  await act(async () => {
    resolveSuperseded?.({ sources: [supersededSource] });
  });

  expect(screen.getByRole("option", { name: "31.0 · Work Styles" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "30.0 · Abilities" })).not.toBeInTheDocument();
  expect(fetchRatingSourceOccupations).not.toHaveBeenCalledWith(
    "token-old",
    "onet-30.0",
    "abilities",
  );
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { SourceResearchPanel } from "./SourceResearchPanel";

const { fetchPostSourceResearch, researchPostSources } = vi.hoisted(() => ({
  fetchPostSourceResearch: vi.fn(),
  researchPostSources: vi.fn(),
}));

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchPostSourceResearch,
  researchPostSources,
}));

beforeEach(() => {
  fetchPostSourceResearch.mockReset();
  researchPostSources.mockReset();
});

it("shows only persisted cited evidence and refreshes it through the explicit admin action", async () => {
  fetchPostSourceResearch
    .mockResolvedValueOnce({ post_id: "post-1", research: [] })
    .mockResolvedValueOnce({
      post_id: "post-1",
      research: [{
        lead_ordinal: 1,
        lead_type_code: "source_reference_url",
        query_text: "https://example.test/patent",
        evidence_text: "Address and patent URL",
        source_content_unit_id: "content-unit-1",
        source_image_region_id: null,
        research_status_code: "supported",
        sharing_actor_name: "Example Research Institute",
        rationale_text: "The cited page explicitly names its publisher.",
        retrievals: [
          {
            url: "https://example.test/cited",
            title: "Patent record",
            passage_text: "Synthetic Publisher is named in this bounded passage.",
            cited: true,
          },
          {
            url: "https://example.test/untitled",
            title: "",
            passage_text: "A second bounded synthetic passage.",
            cited: true,
          },
          { url: "https://example.test/unused", title: "Unused result", passage_text: "...", cited: false },
        ],
      }],
    });
  researchPostSources.mockResolvedValue({ post_id: "post-1", researched_count: 1 });

  render(<SourceResearchPanel postId="post-1" accessToken="token" canResearch />);
  expect(await screen.findByText("No persisted source research yet.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Research sources" }));

  expect(await screen.findByText("Example Research Institute")).toBeInTheDocument();
  expect(screen.getByText("Synthetic Publisher is named in this bounded passage.")).toBeInTheDocument();
  expect(screen.getByText(/content-unit-1/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open source in new tab: Patent record" })).toHaveAttribute(
    "href",
    "https://example.test/cited",
  );
  expect(screen.getByRole("link", { name: "Open source in new tab: https://example.test/untitled" })).toHaveAttribute(
    "href",
    "https://example.test/untitled",
  );
  expect(screen.getByText(/Next action/)).toBeInTheDocument();
  expect(screen.queryByText("Unused result")).not.toBeInTheDocument();
  await waitFor(() => expect(researchPostSources).toHaveBeenCalledWith("token", "post-1"));
});

it("keeps an uncertain lead actorless and hides the admin action from readers", async () => {
  fetchPostSourceResearch.mockResolvedValue({
    post_id: "post-1",
    research: [{
      lead_ordinal: 1,
      lead_type_code: "patent_reference",
      query_text: "US-000000",
      evidence_text: "123 Example Street",
      source_content_unit_id: null,
      source_image_region_id: "image-region-1",
      research_status_code: "not_enough_information",
      sharing_actor_name: null,
      rationale_text: "No retrieved passage identifies a publisher.",
      retrievals: [],
    }],
  });

  render(<SourceResearchPanel postId="post-1" accessToken="token" canResearch={false} />);
  expect(await screen.findByText("Not enough information")).toBeInTheDocument();
  expect(screen.getByText(/do not infer a sharing actor/i)).toBeInTheDocument();
  expect(screen.getByText(/image-region-1/)).toBeInTheDocument();
  expect(screen.getByText("Review source evidence for this dimension.")).toBeInTheDocument();
  expect(screen.queryByText("Sharing actor")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Research sources" })).not.toBeInTheDocument();
});

it("does not render a TypeError when source research fails", async () => {
  fetchPostSourceResearch.mockRejectedValue(
    new TypeError("Cannot read properties of undefined (reading 'choices')"),
  );
  render(<SourceResearchPanel postId="post-1" accessToken="token" canResearch />);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Source reference research could not be completed.");
  expect(alert).toHaveTextContent("Retry, or continue with saved evidence.");
  expect(alert).not.toHaveTextContent(/TypeError|choices/i);
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

it("retries a failed persisted-evidence read", async () => {
  fetchPostSourceResearch
    .mockRejectedValueOnce(new Error("temporary read failure"))
    .mockResolvedValueOnce({ post_id: "post-1", research: [] });

  render(<SourceResearchPanel postId="post-1" accessToken="token" canResearch />);
  fireEvent.click(await screen.findByRole("button", { name: "Retry" }));

  expect(await screen.findByText("No persisted source research yet.")).toBeInTheDocument();
  expect(fetchPostSourceResearch).toHaveBeenCalledTimes(2);
});

it("shows reader-safe next-action copy when explicit research fails", async () => {
  fetchPostSourceResearch.mockResolvedValue({ post_id: "post-1", research: [] });
  researchPostSources.mockRejectedValue(new Error("temporary research failure"));

  render(<SourceResearchPanel postId="post-1" accessToken="token" canResearch />);
  fireEvent.click(await screen.findByRole("button", { name: "Research sources" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Source reference research could not be completed.");
  expect(alert).toHaveTextContent("Retry, or continue with saved evidence.");
});

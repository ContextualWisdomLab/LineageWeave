import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { OccupationRatingProfile, OccupationRatingProfileView } from "./OccupationRatingProfile";
import "../App.css";

const ready = {
  data_release_code: "onet-31.0", source_table_code: "abilities", onetsoc_code: "15-1252.00", source_available: true,
  source: { source_table_name: "Abilities", source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64), source_row_count: 94640, scale_artifact_url: "https://example.test/scales.csv", scale_artifact_sha256: "b".repeat(64), scale_source_row_count: 33 },
  items: [
    { element_id: "1.A.1.a.1", element_name: "Oral Comprehension", scale_id: "IM", scale_name: "Importance", minimum_value: "1.00", maximum_value: "5.00", category_value: null, data_value: "4.10", sample_size: 120, standard_error: "0.0800", lower_ci_bound: "3.9432", upper_ci_bound: "4.2568", recommend_suppress: true, not_relevant: null, source_updated_month: "08/2026", domain_source_code: "Analyst" },
    { element_id: "1.A.1.a.2", element_name: "Written Comprehension", scale_id: "LV", scale_name: "Level", minimum_value: "0.00", maximum_value: "7.00", category_value: null, data_value: "5.25", sample_size: 118, standard_error: "0.1100", lower_ci_bound: "5.0344", upper_ci_bound: "5.4656", recommend_suppress: false, not_relevant: false, source_updated_month: "08/2026", domain_source_code: "Analyst" },
  ],
  next_offset: null,
};

const meta = { title: "Ontology/OccupationRatingProfile", component: OccupationRatingProfileView, parameters: { layout: "fullscreen" }, args: { profile: ready } } satisfies Meta<typeof OccupationRatingProfileView>;
export default meta;
type Story = StoryObj<typeof meta>;

export const EvidenceReady: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("4.10")).toBeVisible();
    await expect(canvas.getByText(/정밀도가 낮아/)).toBeVisible();
  },
};

export const InteractiveEvidenceReady: Story = {
  render: () => <OccupationRatingProfile accessToken="synthetic-token" />,
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify(ready), {
      headers: { "Content-Type": "application/json" },
    });
    return () => { globalThis.fetch = previousFetch; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("O*NET-SOC 직업 코드"), "15-1252.00");
    await userEvent.click(canvas.getByRole("button", { name: "직업 근거 열기" }));
    await expect(canvas.findByText("4.10")).resolves.toBeVisible();
  },
};

export const NarrowViewport: Story = {
  ...InteractiveEvidenceReady,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
export const SourceUnavailable: Story = { args: { profile: { ...ready, source_available: false, source: null, items: [] } } };
export const EmptyOccupation: Story = { args: { profile: { ...ready, items: [] } } };

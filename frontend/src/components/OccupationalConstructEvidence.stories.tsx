import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { OccupationalConstructEvidence } from "./OccupationalConstructEvidence";
import "../App.css";

const assertion = {
  construct_iri: "https://data.onetcenter.org/element/1.A.1.a.1",
  construct_family_code: "cognitive_ability",
  preferred_label: "Oral Comprehension",
  vocabulary_iri: "https://www.onetcenter.org/database.html",
  vocabulary_version: "31.0",
  evidence_text: "The synthetic reviewer compared the written procedure with the inspection record.",
  truth_status_code: "truth_inferred",
  extraction_method: "contextual_orchestrator_onet_hierarchy_v1",
  generated_at: "2026-08-27T00:00:00Z",
  unit_index: 1,
  provenance: "post_occupational_construct_assertion.evidence_text",
};

const meta = {
  title: "Post/Occupational construct evidence",
  component: OccupationalConstructEvidence,
  parameters: { layout: "padded" },
} satisfies Meta<typeof OccupationalConstructEvidence>;

export default meta;
type Story = StoryObj<typeof meta>;

export const EvidenceReady: Story = {
  args: { status: "complete", assertions: [assertion] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("link", { name: "Open catalog definition" })).toHaveAttribute(
      "href",
      assertion.construct_iri,
    );
    await userEvent.click(canvas.getByText("Evidence details"));
    await expect(canvas.getByRole("img", { name: /Inference:/ })).toBeVisible();
  },
};

export const NoSupportedEvidence: Story = { args: { status: "complete", assertions: [] } };
export const Processing: Story = { args: { status: "processing", assertions: [] } };
export const Unavailable: Story = { args: { status: "unavailable", assertions: [] } };
export const HistoricalCutoffUnavailable: Story = {
  args: { status: "historical_unavailable", assertions: [] },
};
export const NarrowViewport: Story = {
  args: { status: "complete", assertions: [assertion] },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

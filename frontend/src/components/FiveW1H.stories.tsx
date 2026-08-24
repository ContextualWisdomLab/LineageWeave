import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import type { FiveW1HSlot } from "../api";
import { FiveW1H } from "./FiveW1H";

const GROUNDED_SLOTS: FiveW1HSlot[] = [
  {
    slot_code: "who",
    values: [
      {
        text: "Demo Corp procurement team",
        source: "post_summary_role",
        evidence_text: "Demo Corp procurement team requested the change.",
        ontology_codes: [],
        ontology_annotations: {},
      },
    ],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
  {
    slot_code: "what",
    values: [
      {
        text: "Cutoff valve replacement",
        source: "post_summary_event",
        evidence_text: "Replace the cutoff valve before the next inspection window.",
        ontology_codes: ["lw:CutoffValveReplacement"],
        ontology_annotations: { ontology_label: "Equipment replacement" },
      },
    ],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
  {
    slot_code: "when",
    values: [],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
  {
    slot_code: "where",
    values: [],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
  {
    slot_code: "why",
    values: [],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
  {
    slot_code: "how",
    values: [],
    empty_next_action_code: "inspect_source_body_or_related_posts",
  },
];

const meta = {
  title: "Evidence/FiveW1H",
  component: FiveW1H,
  args: {
    slots: GROUNDED_SLOTS,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof FiveW1H>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Populated: Story = {};

export const Loading: Story = {
  args: { slots: null },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Loading 5W1H...")).toBeInTheDocument();
  },
};

export const AllDimensionsEmpty: Story = {
  args: {
    slots: GROUNDED_SLOTS.map((slot) => ({ ...slot, values: [] })),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const emptyMessages = canvas.getAllByText("No grounded evidence for this dimension.");
    await expect(emptyMessages).toHaveLength(GROUNDED_SLOTS.length);
  },
};

export const EvidenceProvenanceExpandable: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const details = canvas.getAllByText("Evidence provenance")[0]
      .closest("details");
    await expect(details).not.toBeNull();
    await expect(details).not.toHaveAttribute("open");
  },
};

// Edge case: an evidence source with no human-label mapping yet must still
// render something readable instead of disappearing.
export const UnmappedEvidenceSource: Story = {
  args: {
    slots: [
      {
        slot_code: "how",
        empty_next_action_code: "none",
        values: [
          {
            text: "Filed via the vendor portal",
            source: "some_future_source",
            ontology_codes: [],
            ontology_annotations: {},
          },
        ],
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("some_future_source")).toBeInTheDocument();
  },
};

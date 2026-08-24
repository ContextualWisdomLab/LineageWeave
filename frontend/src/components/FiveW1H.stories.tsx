import type { Meta, StoryObj } from "@storybook/react-vite";
import { FiveW1H } from "./FiveW1H";

const meta = {
  title: "Ask Agent/FiveW1H",
  component: FiveW1H,
} satisfies Meta<typeof FiveW1H>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Loading: Story = {
  args: { slots: null },
};

export const AllSlotsEmpty: Story = {
  args: {
    slots: (["who", "what", "when", "where", "why", "how"] as const).map((slot_code) => ({
      slot_code,
      values: [],
      empty_next_action_code: "none",
    })),
  },
};

export const GroundedAnswer: Story = {
  args: {
    slots: [
      {
        slot_code: "who",
        empty_next_action_code: "none",
        values: [
          {
            text: "Ada West",
            source: "post_summary_role",
            evidence_text: "“Ada West signed off on the renewal”",
            ontology_codes: [],
            ontology_annotations: {},
          },
          {
            text: "Northwind Logistics",
            source: "post_summary_role.affiliated_organization_name",
            ontology_codes: [],
            ontology_annotations: {},
          },
        ],
      },
      {
        slot_code: "what",
        empty_next_action_code: "none",
        values: [
          {
            text: "Renewed the vendor contract",
            source: "post_summary_event",
            evidence_text: "“we renewed the contract through Q4”",
            ontology_codes: ["evt-42"],
            ontology_annotations: { ontology_label: "Contract renewal" },
          },
        ],
      },
      {
        slot_code: "when",
        empty_next_action_code: "none",
        values: [],
      },
    ],
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
};

import type { Meta, StoryObj } from "@storybook/react-vite";
import type { OccupationalConstructSearchPage } from "../api";
import { OccupationalConstructCatalogSearch } from "./OccupationalConstructCatalogSearch";

const populated: OccupationalConstructSearchPage = {
  query: "Oral",
  family_code: "cognitive_ability",
  next_cursor: null,
  hits: [
    {
      construct_id: "99999999-9999-9999-9999-999999999999",
      construct_iri: "https://data.onetcenter.org/element/1.A.1.a.1",
      construct_family_code: "cognitive_ability",
      preferred_label: "Oral Comprehension",
      vocabulary_version: "31.0",
      supporting_post_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
      supporting_post_title: "Synthetic briefing",
      evidence_text: "reviewed the written procedure",
      truth_status_code: "truth_inferred",
    },
  ],
};

const meta = {
  title: "Evidence/OccupationalConstructCatalogSearch",
  component: OccupationalConstructCatalogSearch,
} satisfies Meta<typeof OccupationalConstructCatalogSearch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Idle: Story = {};

export const Populated: Story = {
  args: {
    page: populated,
    status: "ready",
  },
};

export const NoMatches: Story = {
  args: {
    page: { query: "Oral", family_code: null, next_cursor: null, hits: [] },
    status: "empty",
  },
};

export const Loading: Story = {
  args: {
    status: "loading",
  },
};

export const Unavailable: Story = {
  args: {
    status: "error",
  },
};

export const NarrowViewport: Story = {
  args: {
    page: populated,
    status: "ready",
  },
  globals: {
    viewport: { value: "mobile1", isRotated: false },
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 402 }}>
        <Story />
      </div>
    ),
  ],
};

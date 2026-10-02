import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
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

let completeEarlierSearch: (() => void) | undefined;

export const SupersededSearch: Story = {
  args: { accessToken: "synthetic-token" },
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      const url = new URL(String(input), window.location.origin);
      if (url.searchParams.get("q") === "Oral") {
        return new Promise<Response>((resolve) => {
          completeEarlierSearch = () => resolve(new Response(JSON.stringify(populated), {
            headers: { "Content-Type": "application/json" },
          }));
        });
      }
      return new Response(JSON.stringify({
        ...populated, query: "Written", hits: [{
          ...populated.hits[0], preferred_label: "Written Comprehension",
        }],
      }), { headers: { "Content-Type": "application/json" } });
    };
    return () => { globalThis.fetch = previousFetch; completeEarlierSearch = undefined; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const query = canvas.getByLabelText(/Catalog label|카탈로그 명칭/);
    const submit = canvas.getByRole("button", { name: /Find matching records|일치하는 기록 찾기/ });
    await userEvent.type(query, "Oral");
    await userEvent.click(submit);
    await waitFor(() => expect(completeEarlierSearch).toBeDefined());
    await userEvent.clear(query);
    await userEvent.type(query, "Written");
    await userEvent.click(submit);
    await expect(canvas.findByRole("button", { name: /Written Comprehension/ })).resolves.toBeVisible();
    completeEarlierSearch?.();
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    await waitFor(() => expect(canvas.queryByRole("button", { name: /Oral Comprehension/ })).not.toBeInTheDocument());
    await expect(canvas.getByRole("button", { name: /Written Comprehension/ })).toBeVisible();
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

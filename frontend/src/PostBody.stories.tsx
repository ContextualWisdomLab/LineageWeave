import type { Meta, StoryObj } from "@storybook/react-vite";
import { PostBody } from "./PostBody";

const meta = {
  title: "Evidence/PostBody",
  component: PostBody,
} satisfies Meta<typeof PostBody>;

export default meta;

type Story = StoryObj<typeof meta>;

const TINY_PNG =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

export const MarkdownTableEvidence: Story = {
  args: {
    body: "| Workstream | State |\n| --- | --- |\n| Alpha | Ready |",
    structureUnits: [
      {
        unit_index: 0,
        unit_kind_code: "plain_text",
        unit_label: "markdown_tr",
        unit_text: "Workstream | State",
        indent_level: 0,
        indent_source_code: "unresolved",
        indent_confidence: 0,
        indent_evidence: "Markdown table row",
      },
      {
        unit_index: 1,
        unit_kind_code: "plain_text",
        unit_label: "markdown_tr",
        unit_text: "Alpha | Ready",
        indent_level: 0,
        indent_source_code: "unresolved",
        indent_confidence: 0,
        indent_evidence: "Markdown table row",
      },
    ],
  },
};

export const MarkdownTableFallback: Story = {
  args: {
    body: "Intro.\n\n| Workstream | State |\n| --- | --- |\n| Alpha | Ready |\n\nNext action.",
  },
};

export const ImageOcrTableEvidence: Story = {
  args: {
    body: `<img src="data:image/png;base64,${TINY_PNG}" />`,
    imageContent: [
      {
        unit_index: 0,
        mime_type: "image/png",
        status_code: "completed",
        extracted_text: "| Workstream | State |\n| --- | --- |\n| Alpha | Ready |",
        caption: "A synthetic workstream status table.",
        tags: ["table"],
      },
    ],
  },
};

export const NumericFootnote: Story = {
  args: {
    body: "<p>Evidence remains attached to the source.</p><p><sup>1</sup> Source note.</p>",
  },
};

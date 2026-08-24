import type { Meta, StoryObj } from "@storybook/react-vite";
import { AskEvidenceLayerPopup } from "./AskEvidenceLayerPopup";

const meta = {
  title: "Evidence/AskEvidenceLayerPopup",
  component: AskEvidenceLayerPopup,
  args: {
    postId: "post-demo-public",
    postTitle: "Checkout error follow-up",
    facts: [
      { kind: "semantic_project", text: "project: Checkout revamp | evidence: Body evidence" },
      { kind: "semantic_keyman", text: "Keyman mention: Ada West | context: account lead" },
    ],
    images: [
      {
        unit_index: 1,
        caption: "Screenshot of the checkout error",
        extracted_text: "Error code 500 on checkout",
        tags: ["screenshot", "error"],
      },
    ],
    onClose: () => undefined,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof AskEvidenceLayerPopup>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const TextEvidenceOnly: Story = {
  args: {
    images: [],
  },
};

export const ImageEvidenceOnly: Story = {
  args: {
    facts: [],
  },
};

// Edge case: a citation with no persisted evidence facts or images at all --
// must show an explicit placeholder, never a blank panel.
export const NoEvidence: Story = {
  args: {
    facts: [],
    images: [],
  },
};

// Edge case: an image evidence entry whose OCR text was never extracted.
export const ImageWithoutExtractedText: Story = {
  args: {
    facts: [],
    images: [
      {
        unit_index: 0,
        caption: "Architecture diagram",
        extracted_text: null,
        tags: [],
      },
    ],
  },
};

// Edge case: an untitled/uncaptioned image.
export const UntitledImage: Story = {
  args: {
    facts: [],
    images: [
      {
        unit_index: 0,
        caption: null,
        extracted_text: null,
        tags: [],
      },
    ],
  },
};

// Edge case: some sources persist an empty caption rather than null. The buyer
// still needs a visible label that explains what to do with the evidence row.
export const BlankImageCaption: Story = {
  args: {
    facts: [],
    images: [
      {
        unit_index: 0,
        caption: "",
        extracted_text: "Diagram OCR text remains available",
        tags: [],
      },
    ],
  },
};

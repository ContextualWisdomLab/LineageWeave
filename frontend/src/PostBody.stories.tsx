import type { Meta, StoryObj } from "@storybook/react-vite";
import { PostBody } from "./PostBody";
import diagramSrc from "./fixtures/synthetic-process-diagram.png?inline";

const meta = {
  title: "Evidence/PostBody",
  component: PostBody,
} satisfies Meta<typeof PostBody>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ImageRegionLocations: Story = {
  args: {
    body: `<img src="${diagramSrc}" alt="" />`,
    imageContent: [
      {
        unit_index: 0,
        mime_type: "image/png",
        status_code: "described",
        extracted_text: "Demo Corp process diagram",
        caption: "A process diagram",
        tags: ["diagram", "process"],
        regions: [
          {
            region_index: 0,
            x_ratio: 0.1,
            y_ratio: 0.2,
            width_ratio: 0.3,
            height_ratio: 0.4,
            status_code: "described",
            extracted_text: "Title block",
            caption: "Title block",
            tags: ["title"],
          },
          {
            region_index: 1,
            x_ratio: 0.5,
            y_ratio: 0.18,
            width_ratio: 0.4,
            height_ratio: 0.28,
            status_code: "described",
            extracted_text: "1. Capture 2. Fuse 3. Land",
            caption: "Process steps",
            tags: ["steps"],
          },
          {
            region_index: 2,
            x_ratio: 0.5,
            y_ratio: 0.55,
            width_ratio: 0.4,
            height_ratio: 0.3,
            status_code: "described",
            extracted_text: "Synthetic fixture only",
            caption: "Notes",
            tags: ["notes"],
          },
        ],
      },
    ],
  },
};

export const WhitespaceCaptionFallsBack: Story = {
  args: {
    body: `<img src="${diagramSrc}" alt="" />`,
    imageContent: [
      {
        unit_index: 0,
        mime_type: "image/png",
        status_code: "described",
        extracted_text: null,
        caption: "   ",
        tags: [],
      },
    ],
  },
};

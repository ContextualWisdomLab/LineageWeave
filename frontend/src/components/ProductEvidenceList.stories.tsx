import type { Meta, StoryObj } from "@storybook/react";
import { ProductEvidenceList } from "./ProductEvidenceList";

const meta = {
  title: "Post/ProductEvidenceList",
  component: ProductEvidenceList,
} satisfies Meta<typeof ProductEvidenceList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CatalogLinked: Story = {
  args: {
    products: [{
      mention_ordinal: 0,
      extracted_product_name: "Synthetic Model Q",
      canonical_product_name: "Synthetic Model Q",
      product_level_code: "product_model",
      resolution_status_code: "unique",
      evidence_text: "Synthetic Model Q was selected for the trial.",
      evidence_post_id: "synthetic-post",
      relations: [{
        relation_type_code: "used_by_project",
        target_kind_code: "project",
        target_id: "synthetic-project",
        target_label: "Synthetic Project",
        evidence_text: "Synthetic Model Q supports the Synthetic Project trial.",
        evidence_post_id: "synthetic-post",
      }],
    }],
  },
};

export const CatalogReviewRequired: Story = {
  args: {
    products: [{
      mention_ordinal: 0,
      extracted_product_name: "Synthetic Model Q",
      canonical_product_name: null,
      product_level_code: null,
      resolution_status_code: "tie",
      evidence_text: "Synthetic Model Q was selected for the trial.",
      evidence_post_id: "synthetic-post",
    }],
  },
};

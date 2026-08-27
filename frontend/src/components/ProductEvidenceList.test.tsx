import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductEvidenceList } from "./ProductEvidenceList";

describe("ProductEvidenceList", () => {
  it("shows the next catalog action only for an unresolved identity", () => {
    render(<ProductEvidenceList products={[{
      mention_ordinal: 0,
      extracted_product_name: "Synthetic Model Q",
      canonical_product_name: null,
      product_level_code: null,
      resolution_status_code: "tie",
      evidence_text: "Synthetic Model Q",
      evidence_post_id: "synthetic-post",
    }]} />);
    expect(screen.getByRole("status")).toHaveTextContent("product catalog");
  });

  it("shows the authorized target and its cited relationship evidence", () => {
    render(<ProductEvidenceList products={[{
      mention_ordinal: 0,
      extracted_product_name: "Synthetic Model Q",
      canonical_product_name: "Synthetic Model Q",
      product_level_code: "product_model",
      resolution_status_code: "unique",
      evidence_text: "Synthetic Model Q",
      evidence_post_id: "synthetic-post",
      relations: [{
        relation_type_code: "used_by_project",
        target_kind_code: "project",
        target_id: "synthetic-project",
        target_label: "Synthetic Project",
        evidence_text: "Synthetic Model Q supports Synthetic Project",
        evidence_post_id: "synthetic-post",
      }],
    }]} />);
    expect(screen.getByText("Synthetic Project")).toBeInTheDocument();
    expect(screen.getByText(/supports Synthetic Project/)).toBeInTheDocument();
  });
});

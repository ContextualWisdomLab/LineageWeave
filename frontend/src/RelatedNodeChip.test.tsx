import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { RelatedNode } from "./api";
import { RelatedNodeChip } from "./RelatedNodeChip";
import { relatedNodeChipAccessibleName } from "./relatedNodeCaption";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

describe("RelatedNodeChip", () => {
  it("keeps the visible plural caption inside the walk name", () => {
    const caption = "Priya Nair, multiple organizations (Counterparty)";
    expect(relatedNodeChipAccessibleName(caption, "walk_person")).toBe(
      `Related nodes for ${caption}`,
    );
    render(
      <RelatedNodeChip
        node={node({
          node_type_code: "node_person",
          label: "Priya Nair",
          person_side_label: "Counterparty",
          affiliation_ambiguous: true,
        })}
        action="walk_person"
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: `Related nodes for ${caption}` })).toHaveTextContent(
      caption,
    );
  });

  it("opens the post when the buyer clicks a title-only chip", async () => {
    const onSelect = vi.fn();
    render(
      <RelatedNodeChip
        node={node({
          node_type_code: "node_post",
          node_id: "post-1",
          label: "Linked post",
        })}
        action="open_post"
        onSelect={onSelect}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Open related post: Linked post" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].node_id).toBe("post-1");
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { RelatedNode } from "./api";
import { RelatedNodeChip } from "./RelatedNodeChip";
import {
  UniqueAffiliation,
  SideOnlyPluralAffiliations,
} from "./RelatedNodeChip.stories";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

describe("RelatedNodeChip", () => {
  it("keeps the unique-affiliation caption inside the walk name", () => {
    const caption = "Ada West, Demo Corp (Our side)";
    render(
      <RelatedNodeChip
        node={UniqueAffiliation.args.node}
        action={UniqueAffiliation.args.action}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: `Related nodes for ${caption}` })).toHaveTextContent(
      caption,
    );
  });

  it("does not invent a primary org on a side-only chip", () => {
    const caption = "Priya Nair (Counterparty)";
    render(
      <RelatedNodeChip
        node={SideOnlyPluralAffiliations.args.node}
        action={SideOnlyPluralAffiliations.args.action}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: `Related nodes for ${caption}` })).toHaveTextContent(
      caption,
    );
    expect(screen.queryByText(/Northridge/)).not.toBeInTheDocument();
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

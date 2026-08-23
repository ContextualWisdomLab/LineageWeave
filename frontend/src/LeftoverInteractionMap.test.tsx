import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LeftoverInteractionMap, projectLeftoverMap } from "./LeftoverInteractionMap";

const itemLabel = (code: string) => (code === "sales_lead_specificity" ? "sales-lead" : code);

describe("LeftoverInteractionMap", () => {
  it("projects coincident origin points to the map center", () => {
    const projected = projectLeftoverMap(
      [{ post_id: "post-1", post_title: "Public post", axis_one: 0, axis_two: 0 }],
      [{ criterion_code: "sales_lead_specificity", axis_one: 0, axis_two: 0 }],
      itemLabel,
      [],
      360,
      240,
      36,
    );
    expect(projected.persons[0]).toMatchObject({ x: 180, y: 120 });
    expect(projected.items[0]).toMatchObject({ x: 180, y: 120 });
  });

  it("renders closest and farthest leftover-map nodes and opens a post", async () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverInteractionMap
        persons={[
          { post_id: "post-1", post_title: "Public post", axis_one: -0.5, axis_two: 0.1 },
          {
            post_id: "post-2",
            post_title: "Specification revision requested",
            axis_one: 0.8,
            axis_two: -0.4,
          },
        ]}
        items={[
          { criterion_code: "sales_lead_specificity", axis_one: -0.4, axis_two: 0.05 },
          { criterion_code: "general_sentiment_negative", axis_one: 1.2, axis_two: -0.9 },
        ]}
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-1",
            post_title: "Public post",
            criterion_code: "sales_lead_specificity",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
          },
          {
            pair_kind: "farthest",
            post_id: "post-2",
            post_title: "Specification revision requested",
            criterion_code: "general_sentiment_negative",
            leftover_distance: 1.84,
            leftover_residual: -1.1,
          },
        ]}
        itemLabel={itemLabel}
        onSelectPost={onSelectPost}
      />,
    );

    expect(screen.getByRole("group", { name: "Leftover interaction map" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open leftover map post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open leftover map post: Public post" }));
    expect(onSelectPost).toHaveBeenCalledWith("post-1");
  });

  it("preserves closest and farthest emphasis on the same node", () => {
    const projected = projectLeftoverMap(
      [{ post_id: "post-1", post_title: "Public post", axis_one: 0, axis_two: 0 }],
      [
        { criterion_code: "item-a", axis_one: -1, axis_two: 0 },
        { criterion_code: "item-b", axis_one: 1, axis_two: 0 },
      ],
      itemLabel,
      [
        {
          pair_kind: "closest",
          post_id: "post-1",
          post_title: "Public post",
          criterion_code: "item-a",
          leftover_distance: 1,
          leftover_residual: 0,
        },
        {
          pair_kind: "farthest",
          post_id: "post-1",
          post_title: "Public post",
          criterion_code: "item-b",
          leftover_distance: 1,
          leftover_residual: 0,
        },
      ],
    );

    expect(projected.persons[0]).toMatchObject({ pairKinds: ["closest", "farthest"] });
  });
});

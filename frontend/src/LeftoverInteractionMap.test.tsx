import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  LeftoverInteractionMap,
  leftoverPairForCriterion,
  projectLeftoverMap,
} from "./LeftoverInteractionMap";
import type { LeftoverPair } from "./api";

const itemLabel = (code: string) => (code === "sales_lead_specificity" ? "sales-lead" : code);

const closestPair: LeftoverPair = {
  pair_kind: "closest",
  post_id: "post-1",
  post_title: "Public post",
  criterion_code: "sales_lead_specificity",
  leftover_distance: 0.12,
  leftover_residual: 0.4,
  observed_response: 2.4,
  expected_response: 2.0,
  leftover_map_rank: 1,
};

const farthestPair: LeftoverPair = {
  pair_kind: "farthest",
  post_id: "post-2",
  post_title: "Specification revision requested",
  criterion_code: "general_sentiment_negative",
  leftover_distance: 1.84,
  leftover_residual: -1.1,
  observed_response: 0.9,
  expected_response: 2.0,
  leftover_map_rank: 1,
};

describe("leftoverPairForCriterion", () => {
  it("prefers the closest leftover pair for a criterion", () => {
    const both: LeftoverPair[] = [
      farthestPair,
      closestPair,
      {
        ...farthestPair,
        pair_kind: "farthest",
        post_id: "post-9",
        criterion_code: "sales_lead_specificity",
      },
    ];
    expect(leftoverPairForCriterion(both, "sales_lead_specificity")).toMatchObject({
      pair_kind: "closest",
      post_id: "post-1",
    });
  });

  it("uses the farthest leftover pair when the criterion is not closest", () => {
    expect(leftoverPairForCriterion([closestPair, farthestPair], "general_sentiment_negative")).toMatchObject({
      pair_kind: "farthest",
      post_id: "post-2",
    });
  });

  it("returns null when the criterion is not a leftover-pair member", () => {
    expect(leftoverPairForCriterion([closestPair, farthestPair], "general_sentiment_positive")).toBeNull();
  });
});

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

  it("uses one common scale for both Gabriel axes", () => {
    const projected = projectLeftoverMap(
      [
        { post_id: "origin", post_title: "Origin", axis_one: 0, axis_two: 0 },
        { post_id: "x", post_title: "X", axis_one: 1, axis_two: 0 },
      ],
      [{ criterion_code: "y", axis_one: 0, axis_two: 1 }],
      itemLabel,
    );
    const origin = projected.persons[0];
    expect(projected.persons[1].x - origin.x).toBeCloseTo(origin.y - projected.items[0].y);
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
        pairs={[closestPair, farthestPair]}
        itemLabel={itemLabel}
        onSelectPost={onSelectPost}
      />,
    );

    expect(screen.getByRole("group", { name: "Leftover interaction map" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open post: Specification revision requested" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open this leftover map criterion to read the leftover pair post: general_sentiment_negative",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open leftover map post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open leftover map post: Public post" }));
    expect(onSelectPost).toHaveBeenCalledWith("post-1");
  });

  it("opens the leftover-pair post from a pair-member criterion node", async () => {
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
          { criterion_code: "general_sentiment_positive", axis_one: 0.1, axis_two: 0.7 },
        ]}
        pairs={[closestPair, farthestPair]}
        itemLabel={itemLabel}
        onSelectPost={onSelectPost}
      />,
    );

    const criterion = screen.getByRole("button", { name: "Open leftover map criterion: sales-lead" });
    expect(criterion).toBeInTheDocument();
    await userEvent.click(criterion);
    expect(onSelectPost).toHaveBeenCalledWith("post-1");
    expect(
      screen.queryByRole("button", { name: "Open leftover map criterion: general_sentiment_positive" }),
    ).not.toBeInTheDocument();
  });

  it("opens a leftover-pair post from a criterion node with the keyboard", async () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverInteractionMap
        persons={[{ post_id: "post-1", post_title: "Public post", axis_one: -0.5, axis_two: 0.1 }]}
        items={[{ criterion_code: "sales_lead_specificity", axis_one: -0.4, axis_two: 0.05 }]}
        pairs={[closestPair]}
        itemLabel={itemLabel}
        onSelectPost={onSelectPost}
      />,
    );

    const criterion = screen.getByRole("button", { name: "Open leftover map criterion: sales-lead" });
    criterion.focus();
    await userEvent.keyboard("{Enter}");
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

import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { LeftoverPairButton } from "./LeftoverPairButton";
import {
  leftoverCriterionLabel,
  leftoverPairNextAction,
  leftoverPairOpenOptions,
  postQualityCriterionElementId,
  type LeftoverPairOpen,
} from "../leftoverPairGuidance";
import "../App.css";

const closest: LeftoverPairOpen = {
  pair_kind: "closest",
  post_id: "post-1",
  post_title: "Public post",
  criterion_code: "sales_lead_specificity",
};

const farthest: LeftoverPairOpen = {
  pair_kind: "farthest",
  post_id: "post-spec",
  post_title: "Specification revision requested",
  criterion_code: "general_sentiment_negative",
};

function LeftoverLanding({ pair, leftoverDistance }: { pair: LeftoverPairOpen; leftoverDistance: number }) {
  const [focusCode, setFocusCode] = useState<string | null>(null);
  return (
    <section>
      <LeftoverPairButton
        pair={pair}
        leftoverDistance={leftoverDistance}
        onOpen={(_postId, options) => setFocusCode(options.focusCriterionCode)}
      />
      {focusCode ? (
        <p
          id={postQualityCriterionElementId(focusCode)}
          tabIndex={-1}
          aria-current="true"
          role="status"
        >
          Post quality criterion {leftoverCriterionLabel(focusCode)}
        </p>
      ) : null}
    </section>
  );
}

const meta = {
  title: "Analysis/LeftoverPairButton",
  component: LeftoverPairButton,
  parameters: { layout: "padded" },
} satisfies Meta<typeof LeftoverPairButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ClosestPair: Story = {
  args: {
    pair: closest,
    leftoverDistance: 0.12,
    onOpen: () => undefined,
  },
  render: () => <LeftoverLanding pair={closest} leftoverDistance={0.12} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole("button", { name: /open leftover closest pair: public post/i });
    await expect(button).toHaveTextContent(leftoverPairNextAction(closest));
    await userEvent.click(button);
    const landed = canvas.getByRole("status");
    await expect(landed).toHaveAttribute("id", postQualityCriterionElementId(closest.criterion_code));
    await expect(landed).toHaveAttribute("aria-current", "true");
    await expect(landed).toHaveTextContent(/sales-lead/);
    await expect(leftoverPairOpenOptions(closest)).toEqual({
      focusCriterionCode: "sales_lead_specificity",
    });
  },
};

export const FarthestPair: Story = {
  args: {
    pair: farthest,
    leftoverDistance: 1.84,
    onOpen: () => undefined,
  },
  render: () => <LeftoverLanding pair={farthest} leftoverDistance={1.84} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole("button", {
      name: /open leftover farthest pair: specification revision requested/i,
    });
    await expect(button).toHaveAccessibleName(/specification revision requested/i);
    await expect(button).toHaveAccessibleName(/negative/);
    await userEvent.click(button);
    await expect(canvas.getByRole("status")).toHaveTextContent(/negative/);
  },
};

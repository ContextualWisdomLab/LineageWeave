import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { LineageEntityPicker } from "./LineageEntityPicker";

const demoEntities = [
  { corporate_entity_id: "corp-demo", entity_name: "Demo Corp" },
  { corporate_entity_id: "corp-north", entity_name: "Northridge Grid" },
];

const meta = {
  title: "Analysis/LineageEntityPicker",
  component: LineageEntityPicker,
  args: {
    entities: demoEntities,
    selectedEntityId: "corp-demo",
    onSelectEntityId: () => undefined,
  },
} satisfies Meta<typeof LineageEntityPicker>;

export default meta;

type Story = StoryObj<typeof meta>;

export const TwoAffiliations: Story = {
  render: function TwoAffiliationsStory(args) {
    const [selectedEntityId, setSelectedEntityId] = useState(args.selectedEntityId);
    return (
      <LineageEntityPicker
        {...args}
        selectedEntityId={selectedEntityId}
        onSelectEntityId={setSelectedEntityId}
      />
    );
  },
};

export const SingleAffiliationHidden: Story = {
  args: {
    entities: [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
  },
};

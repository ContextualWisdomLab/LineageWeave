import type { Meta, StoryObj } from "@storybook/react-vite";
import { RoleEvidence } from "./RoleEvidence";
import "../App.css";

const meta = {
  title: "Evidence/RoleEvidence",
  component: RoleEvidence,
  parameters: { layout: "padded" },
  args: {
    actorContent: <strong>Example attendee</strong>,
    actorName: "Example attendee",
    actorTypeCode: "prov_person",
    actorTypeLabel: "Person",
    responsibility: "Meeting attendee",
    affiliationName: "Example organization",
    affiliationCatalogId: "corp-example",
    affiliationLabel: "Affiliation",
    affiliationAriaLabel: "Open affiliation: Example organization",
    unresolvedLabel: "Not linked",
    genericUnitNote: "Specific unit not stated in source",
    onSelectAffiliation: () => undefined,
  },
} satisfies Meta<typeof RoleEvidence>;

export default meta;

type Story = StoryObj<typeof meta>;

export const LinkedAffiliation: Story = {};

export const UnresolvedAffiliation: Story = {
  args: {
    affiliationCatalogId: null,
  },
};

export const GenericBusinessUnit: Story = {
  args: {
    actorContent: <strong>사업부</strong>,
    actorName: "사업부",
    actorTypeCode: "prov_team",
    actorTypeLabel: "Team",
    affiliationName: null,
  },
};

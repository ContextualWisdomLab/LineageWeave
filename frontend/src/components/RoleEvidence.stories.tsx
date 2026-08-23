import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import {
  analysisEvidenceDiagnosis,
  gluedRoleRelationshipNextAction,
} from "../analysisEvidenceDiagnosis";
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
    unresolvedLabel: "Not linked to catalog",
    unresolvedNextAction: analysisEvidenceDiagnosis("catalog_unbound").nextAction,
    relationshipNextAction: gluedRoleRelationshipNextAction(),
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
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText(/Not linked to catalog/)).toBeInTheDocument();
    await expect(canvas.getByText(analysisEvidenceDiagnosis("catalog_unbound").nextAction)).toBeInTheDocument();
    await expect(canvas.queryByText(/missing signal is not a negative fact/i)).not.toBeInTheDocument();
    await expect(canvas.queryByText(/operates/i)).not.toBeInTheDocument();
  },
};

export const EvidenceDiagnosisKinds: Story = {
  render: () => {
    const unbound = analysisEvidenceDiagnosis("catalog_unbound");
    const dropped = analysisEvidenceDiagnosis("dropped_channel");
    const negative = analysisEvidenceDiagnosis("confident_negative");
    return (
      <section>
        <p role="status">{unbound.title}. {unbound.nextAction}</p>
        <p role="status">{dropped.title}. {dropped.nextAction}</p>
        <p role="status">{negative.title}. {negative.nextAction}</p>
      </section>
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const statuses = canvas.getAllByRole("status");
    await expect(statuses).toHaveLength(3);
    await expect(statuses[0]).toHaveTextContent(/unbound/i);
    await expect(statuses[1]).toHaveTextContent(/missing signal is not a negative fact/i);
    await expect(statuses[2]).toHaveTextContent(/measured negative/i);
    await expect(statuses[0].textContent).not.toBe(statuses[1].textContent);
    await expect(statuses[1].textContent).not.toBe(statuses[2].textContent);
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
